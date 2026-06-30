import requests

url = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json"

response = requests.get(url)

print("Status Code:", response.status_code)

with open("catalog_raw.txt", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Saved as catalog_raw.txt")