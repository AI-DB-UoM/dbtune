def suggest_index(table: str, columns: list[str], config: dict, query: list[str]) -> str:
    # replace to real MAB

    tune_via_MAB(table, columns, config, query)

    arm = {"type": "ivfflat", "lists": 101}
    col_str = ", ".join(columns)
    sql = f"CREATE INDEX ON {table} USING {arm['type']} ({col_str})"
    if "lists" in arm:
        sql += f" WITH (lists = {arm['lists']})"
    return sql


def tune_via_MAB(table, columns, config, query):
    print(f"[DEBUG] --------------tune_via_MAB--------------")
    pass