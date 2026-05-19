import os

from bandits.sim_c3ucb_vF import BanditTuner

_TUNER = None


def _get_tuner(config_path: str | None = None):
    global _TUNER
    if _TUNER is None:
        cfg = config_path or os.getenv(
            "DBTUNE_MAB_CONFIG",
            "/app/configs/online_pgdb.yaml",
        )
        _TUNER = BanditTuner(cfg)
    return _TUNER


def _to_create_index_sql(arm) -> str:
    cols = ", ".join(arm.index_cols)
    sql = f"CREATE INDEX IF NOT EXISTS {arm.index_name} ON {arm.table_name} ({cols})"
    if getattr(arm, "include_cols", None):
        include_cols = ", ".join(arm.include_cols)
        sql += f" INCLUDE ({include_cols})"
    return sql + ";"


def suggest_index(table: str, columns: list[str], config: dict, query: list[str]) -> str:
    recommendation_arms = tune_via_MAB(table, columns, config, query)
    if not recommendation_arms:
        raise ValueError("No index recommendation could be generated from the current workload.")
    return _to_create_index_sql(recommendation_arms[0])


def tune_via_MAB(table, columns, config, query):
    print(f"[DEBUG] --------------tune_via_MAB--------------")

    if not table:
        raise ValueError("table is required")

    raw_queries = query or []
    if isinstance(raw_queries, str):
        raw_queries = [q.strip() + ";" for q in raw_queries.split(";") if q.strip()]
    filtered_queries = []
    table_marker = f"from {table.lower()}"
    for q in raw_queries:
        lower_q = q.lower()
        if not (lower_q.startswith("select") or lower_q.startswith("with")):
            continue
        if "dbtune_" in lower_q:
            continue
        if table_marker in lower_q:
            filtered_queries.append(q)

    if not filtered_queries:
        filtered_queries = raw_queries

    top_k = int(config.get("top_k", 3)) if isinstance(config, dict) else 3
    if not filtered_queries and columns:
        conditions = " AND ".join([f"{c} IS NOT NULL" for c in columns])
        filtered_queries = [f"SELECT * FROM {table} WHERE {conditions};"]

    tuner = _get_tuner(config.get("config_file") if isinstance(config, dict) else None)
    return tuner.recommend_index_arms(
        filtered_queries,
        target_table=table,
        top_k=top_k,
        preferred_columns=columns,
    )
