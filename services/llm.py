import os

from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - defensive fallback
    genai = None

api_key = os.getenv("GEMINI_API_KEY")
if genai is not None and api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None


def generate_response(prompt: str) -> str:
    if model is None:
        return (
            "I can help narrow down SHL assessments from the catalog. "
            "Please share the role, seniority, and the type of assessment you need."
        )

    try:
        response = model.generate_content(prompt)
        return getattr(response, "text", "") or (
            "I can only assist with SHL assessment selection and comparison."
        )
    except Exception:
        return "I can only assist with SHL assessment selection and comparison."