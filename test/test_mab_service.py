from pathlib import Path


def load_queries(sql_dir: Path):
    return [path.read_text(encoding="utf-8") for path in sql_dir.glob("*.sql")]


def run_training():
    from dbtune_mab_service.bandits.sim_c3ucb_vF import BanditTuner
    from dbtune_mab_service.db_tools.schema_loader import load_schema_from_ddl_file

    sql_dir = Path("~/Documents/join-order-benchmark").expanduser()
    raw_queries = load_queries(sql_dir)
    if not raw_queries:
        raise RuntimeError(f"No SQL files found under {sql_dir}")

    imdb_schema = load_schema_from_ddl_file("./dbtune_mab_service/schemas/imdb_schema.sql")
    config_paths = [
        "./dbtune_mab_service/configs/test_imdb_batch_10_round_30_hyp_5_budget_25000.yaml",
        "./dbtune_mab_service/configs/test_imdb_batch_10_round_30_hyp_5_budget_100000.yaml",
        "./dbtune_mab_service/configs/test_imdb_batch_10_round_30_hyp_25_budget_25000.yaml",
        "./dbtune_mab_service/configs/test_imdb_batch_10_round_100_hyp_5_budget_25000.yaml",
        "./dbtune_mab_service/configs/test_imdb_batch_20_round_100_hyp_5_budget_25000.yaml",
        "./dbtune_mab_service/configs/test_imdb_batch_50_round_100_hyp_5_budget_25000.yaml",
    ]

    for config in config_paths:
        tuner = BanditTuner(config)
        tuner.init_queries(raw_queries, imdb_schema)
        tuner.train_MAB_via_dead_loop()


if __name__ == "__main__":
    run_training()

