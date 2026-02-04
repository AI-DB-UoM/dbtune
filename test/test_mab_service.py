from dbtune_mab_service.bandits.sim_c3ucb_vF import BanditTuner
# load queries
from pathlib import Path


sql_dir = Path("~/Documents/join-order-benchmark").expanduser()

raw_queries = [
    path.read_text(encoding="utf-8")
    for path in sql_dir.glob("*.sql")
]

# nohup bash python test/test_mab_service.py > /dev/null 2>&1 &


# print(raw_queries[0])

from dbtune_mab_service.db_tools.schema_loader import load_schema_from_ddl_file
imdb_schema = load_schema_from_ddl_file("./dbtune_mab_service/schemas/imdb_schema.sql")

config_path = ["./dbtune_mab_service/configs/test_imdb_batch_10_round_30_hyp_5_budget_25000.yaml",
               "./dbtune_mab_service/configs/test_imdb_batch_10_round_30_hyp_5_budget_100000.yaml",
               "./dbtune_mab_service/configs/test_imdb_batch_10_round_30_hyp_25_budget_25000.yaml",
               "./dbtune_mab_service/configs/test_imdb_batch_10_round_100_hyp_5_budget_25000.yaml",
               "./dbtune_mab_service/configs/test_imdb_batch_20_round_100_hyp_5_budget_25000.yaml",
               "./dbtune_mab_service/configs/test_imdb_batch_50_round_100_hyp_5_budget_25000.yaml",
               ]

# config_path = ["./dbtune_mab_service/configs/debug_batch_4.yaml"]

for config in config_path:
    tuner = BanditTuner(config)
    tuner.init_queries(raw_queries, imdb_schema)
    tuner.train_MAB_via_dead_loop()

# export PYTHONPATH="$PWD:$PYTHONPATH"
# ps aux | grep test/test_mab_service.py
# nohup bash python test/test_mab_service.py > /dev/null 2>&1 &
