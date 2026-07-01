import re
from typing import Any, Dict, List

from services.llm import generate_response
from services.retriever import Retriever




class ChatAgent:
    def __init__(self, retriever):
        self.retriever = retriever

    def _normalize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        if not isinstance(messages, list):
            return normalized

        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "")).strip().lower()
            content = str(message.get("content", "")).strip()
            if role and content:
                normalized.append({"role": role, "content": content})
        return normalized

    def _get_latest_user_message(self, messages: List[Dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return message.get("content", "")
        return ""

    def _build_conversation_query(self, messages: List[Dict[str, Any]]) -> str:
        user_messages = [message.get("content", "") for message in messages if message.get("role") == "user"]
        return " ".join(part for part in user_messages if part).strip()

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        return "\n".join(f"{message['role']}: {message['content']}" for message in messages)

    def _is_off_topic(self, text: str) -> bool:
        lowered = text.lower()
        off_topic_phrases = [
            "legal advice",
            "weather",
            "write python",
            "python code",
            "hire employees",
            "how should i hire",
            "salary",
        ]
        return any(phrase in lowered for phrase in off_topic_phrases)

    def _normalize_name(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip().lower())

    def _extract_comparison_targets(self, text: str) -> List[str]:
        lowered = text.strip()
        if not lowered:
            return []

        patterns = [
            r"\bcompare\s+(.+?)\s+(?:and|vs|versus)\s+(.+)$",
            r"\bdifference\s+between\s+(.+?)\s+(?:and|vs|versus)\s+(.+)$",
            r"\bcomparison\s+between\s+(.+?)\s+(?:and|vs|versus)\s+(.+)$",
            r"(.+?)\s+(?:vs|versus)\s+(.+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if match:
                targets = [part.strip() for part in match.groups() if part and part.strip()]
                if len(targets) >= 2:
                    return targets[:2]

        return []

    def _is_comparison_request(self, text: str) -> bool:
        lowered = text.lower()
        if any(keyword in lowered for keyword in ["difference", "compare", "comparison", "vs", "versus", "between"]):
            return bool(self._extract_comparison_targets(text))
        return False

    def _build_name_aliases(self, entry: Dict[str, Any]) -> List[str]:
        aliases: List[str] = []
        text = str(entry.get("name", "") or "")
        aliases.append(self._normalize_name(text))
        for match in re.findall(r"\(([A-Za-z0-9]+)\)", text):
            aliases.append(self._normalize_name(match))
        for token in re.findall(r"[A-Za-z0-9]+", text):
            if len(token) > 2:
                aliases.append(self._normalize_name(token))
        return [alias for alias in aliases if alias]

    def _build_semantic_aliases(self, entry: Dict[str, Any]) -> List[str]:
        aliases: List[str] = self._build_name_aliases(entry)
        for field in [entry.get("description", ""), entry.get("job_levels", ""), entry.get("test_type", ""), entry.get("keys", "")]:
            text = str(field or "")
            for token in re.findall(r"[A-Za-z0-9]+", text):
                if len(token) > 1:
                    aliases.append(self._normalize_name(token))
        return [alias for alias in aliases if alias]

    def _find_exact_match(self, target: str) -> Dict[str, Any] | None:
        normalized_target = self._normalize_name(target)
        if not normalized_target:
            return None

        for entry in self.retriever.entries:
            entry_name = self._normalize_name(entry.get("name", ""))
            if entry_name == normalized_target:
                return entry

            aliases = self._build_semantic_aliases(entry)
            if any(
                normalized_target == alias
                or normalized_target in alias
                or alias in normalized_target
                for alias in aliases
            ):
                return entry

            if normalized_target in entry_name or entry_name in normalized_target:
                return entry

        return None

    def _resolve_comparison_entries(self, targets: List[str]) -> List[Dict[str, Any]]:
        resolved: List[Dict[str, Any]] = []
        unresolved: List[str] = []

        for target in targets:
            entry = self._find_exact_match(target)
            if entry is not None:
                resolved.append(entry)
            else:
                unresolved.append(target)

        if len(resolved) == 2:
            return resolved

        if unresolved:
            combined_query = " ".join(targets)
            semantic_results = self.retriever.search(combined_query, top_k=8)
            for target in unresolved:
                target_norm = self._normalize_name(target)
                for result in semantic_results:
                    result_name = self._normalize_name(result.get("name", ""))
                    if result_name == target_norm or target_norm in result_name or result_name in target_norm:
                        if result not in resolved:
                            resolved.append(result)
                            break
                    else:
                        aliases = self._build_semantic_aliases(result)
                        if target_norm in aliases:
                            if result not in resolved:
                                resolved.append(result)
                                break

        return resolved[:2]

    def _build_comparison_reply(self, latest_message: str, entries: List[Dict[str, Any]]) -> str:
        if len(entries) != 2:
            return "I could not find both assessments in the catalog."

        def _fmt(value: Any) -> str:
            if value in (None, "", []):
                return "Not listed"
            if isinstance(value, list):
                return ", ".join(str(item) for item in value if item)
            return str(value)

        table_rows = []
        for entry in entries:
            table_rows.append(
                "| {name} | {description} | {duration} | {job_levels} | {test_type} |".format(
                    name=entry.get("name", ""),
                    description=_fmt(entry.get("description") or "No description available."),
                    duration=_fmt(entry.get("duration_minutes") or entry.get("duration")),
                    job_levels=_fmt(entry.get("job_levels")),
                    test_type=_fmt(entry.get("test_type") or entry.get("keys")),
                )
            )

        table = "\n".join(
            [
                "| Assessment | Description | Duration | Job levels | Keys / Test type |",
                "| --- | --- | --- | --- | --- |",
                *table_rows,
            ]
        )

        first_name = entries[0].get("name", "")
        second_name = entries[1].get("name", "")
        first_desc = _fmt(entries[0].get("description") or "No description available.")
        second_desc = _fmt(entries[1].get("description") or "No description available.")

        return (
            "Here is a catalog-grounded comparison:\n\n"
            f"{first_name}: {first_desc}\n"
            f"{second_name}: {second_desc}\n\n"
            f"{table}\n\n"
            "This comparison uses only the catalog information provided."
        )

    def _is_refinement_request(self, text: str, messages: List[Dict[str, Any]]) -> bool:
        lowered = text.lower()
        if not any(word in lowered for word in ["actually", "add", "also", "include", "more", "another", "instead", "replace"]):
            return False
        return len(messages) >= 2

    def _needs_clarification(self, text: str) -> bool:
        lowered = text.lower().strip()
        if lowered in {
            "hiring",
            "hiring someone",
            "need assessment",
            "need an assessment",
            "recommend assessment",
            "recommend assessments",
            "need a test",
            "need test",
            "i need an assessment",
            "i need assessment",
        }:
            return True

        tokens = re.findall(r"[A-Za-z0-9+.-]+", lowered)
        if len(tokens) <= 3 and "assessment" in lowered and "for" not in lowered and "role" not in lowered:
            return True

        return False

    def _format_recommendations(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []
        for item in results[:6]:
            recommendations.append(
                {
                    "name": item.get("name", ""),
                    "url": item.get("url", ""),
                    "test_type": item.get("test_type") or item.get("keys") or "",
                }
            )
        return recommendations

    def _build_recommendation_reply(self, conversation_text: str, results: List[Dict[str, Any]]) -> str:
        context = "\n\n".join(
            f"Name: {item['name']}\nDescription: {item.get('description', '')}\nTest type: {item.get('test_type') or item.get('keys') or ''}"
            for item in results[:6]
        )
        prompt = f"""
You are an SHL assessment recommendation assistant.

Conversation:
{conversation_text}

Retrieved assessments:
{context}

Recommend the most relevant SHL assessments and explain briefly why they fit.
Keep the answer under 150 words.
Only discuss SHL assessments from the catalog.
"""
        return generate_response(prompt)

    def chat(self, messages: List[Dict[str, Any]]):
        normalized_messages = self._normalize_messages(messages)
        if not normalized_messages:
            return {
                "reply": "I can help you select or compare SHL assessments.",
                "recommendations": [],
                "end_of_conversation": False,
            }

        latest_user_message = self._get_latest_user_message(normalized_messages)
        if not latest_user_message:
            return {
                "reply": "I can help you select or compare SHL assessments.",
                "recommendations": [],
                "end_of_conversation": False,
            }

        conversation_text = self._format_conversation(normalized_messages)
        conversation_query = self._build_conversation_query(normalized_messages)

        if self._is_off_topic(latest_user_message):
            return {
                "reply": "I can only assist with SHL assessment selection and comparison.",
                "recommendations": [],
                "end_of_conversation": True,
            }

        if self._is_comparison_request(latest_user_message):
            targets = self._extract_comparison_targets(latest_user_message)
            resolved_entries = self._resolve_comparison_entries(targets)
            reply = self._build_comparison_reply(latest_user_message, resolved_entries)
            return {
                "reply": reply,
                "recommendations": [],
                "end_of_conversation": True,
            }

        if self._is_refinement_request(latest_user_message, normalized_messages):
            retrieved = self.retriever.search(conversation_query, top_k=6)
            recommendations = self._format_recommendations(retrieved)
            reply = self._build_recommendation_reply(conversation_text, retrieved)
            return {
                "reply": reply,
                "recommendations": recommendations,
                "end_of_conversation": False,
            }

        if self._needs_clarification(latest_user_message):
            return {
                "reply": "What role are you hiring for and what skills are most important?",
                "recommendations": [],
                "end_of_conversation": False,
            }

        retrieved = self.retriever.search(conversation_query or latest_user_message, top_k=6)
        recommendations = self._format_recommendations(retrieved)
        reply = self._build_recommendation_reply(conversation_text, retrieved)

        return {
            "reply": reply,
            "recommendations": recommendations,
            "end_of_conversation": False,
        }