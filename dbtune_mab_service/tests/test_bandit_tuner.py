import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bandits.sim_c3ucb_vF import BanditTuner

def test_tuner():
    tuner = BanditTuner()
    # print(tuner)

    # for i, table in enumerate(tuner.tables):
    #     print(table)

    # for i, (query, props) in enumerate(zip(tuner.queries, tuner.query_properties)):
    #     print(f"\n--- Query {i} ---")
    #     print(query)
    #     print("Predicates:")
    #     for table, fields in props.items():
    #         print(f"  {table}: {fields}")

    tuner.train_MAB()
    
if __name__ == "__main__":
    test_tuner()
