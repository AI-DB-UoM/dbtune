def normalize_sql(query: str) -> str:
    # Keep parser behavior minimal for v0.1.1 bootstrap.
    return " ".join(query.strip().split()).lower()
