from services.retriever import Retriever

retriever = Retriever()

queries = [
    "Java developer",
    "Sales executive",
    "Personality assessment",
    "Numerical reasoning",
]

for query in queries:
    print(f"\nQUERY: {query}")
    print("-" * 50)

    results = retriever.search(query, top_k=5)

    for i, result in enumerate(results, start=1):
        print(f"{i}. {result['name']}")
        print(f"   Score: {result['score']:.3f}")
        print()
        