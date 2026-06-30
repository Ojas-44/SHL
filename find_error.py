with open("catalog_raw.txt", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

for i in range(4788, 4802):
    print(f"LINE {i+1}:")
    print(lines[i])
    print("-" * 50)