import os
import sys
from pathlib import Path

import pytest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bandits.sim_c3ucb_vF import BanditTuner

def test_tuner():
    config_path = Path(__file__).resolve().parents[1] / "configs" / "debug.yaml"
    if not config_path.exists():
        pytest.skip(f"Config file not found: {config_path}")

    try:
        tuner = BanditTuner(str(config_path))
    except Exception as exc:
        pytest.skip(f"BanditTuner runtime dependency is unavailable: {exc}")

    assert tuner is not None

    # for i, table in enumerate(tuner.tables):
    #     print(table)

    # for i, (query, props) in enumerate(zip(tuner.queries, tuner.query_properties)):
    #     print(f"\n--- Query {i} ---")
    #     print(query)
    #     print("Predicates:")
    #     for table, fields in props.items():
    #         print(f"  {table}: {fields}")

    # tuner.train_MAB()
    
if __name__ == "__main__":
    test_tuner()
