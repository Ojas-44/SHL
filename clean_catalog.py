import json

with open("catalog_raw.txt", "r", encoding="utf-8") as f:
    data = json.load(f)

clean_data = []

for item in data:
    clean_data.append({
        "name": item.get("name", ""),
        "url": item.get("link", ""),
        "description": item.get("description", ""),
        "job_levels": item.get("job_levels", []),
        "keys": item.get("keys", []),
        "duration": item.get("duration", ""),
        "languages": item.get("languages", [])
    })

with open("catalog.json", "w", encoding="utf-8") as f:
    json.dump(clean_data, f, indent=2)

print(f"Saved {len(clean_data)} assessments")