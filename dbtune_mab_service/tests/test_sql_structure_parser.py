import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db_tools.query_loader import QueryLoader
from db_tools.sql_structure_parser import SQLStructureParser

def load_queries(filepath):
    if filepath.endswith(".sql"):
        return QueryLoader.load_from_sql(filepath)
    elif filepath.endswith(".csv"):
        return QueryLoader.load_from_csv(filepath)
    elif filepath.endswith(".txt"):
        return QueryLoader.load_from_txt(filepath)
    else:
        raise ValueError(f"Unsupported format: {filepath}")

def test_batch_parser():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(base_dir, "workloads", "test_workload.sql")  # modify as needed
    queries = load_queries(path)

    for i, query in enumerate(queries):
        parser = SQLStructureParser(query, query_id=i + 1)
        print(f"\n--- Parsed Query #{i+1} ---")
        for k, v in parser.to_dict().items():
            print(f"{k} = {v}")

if __name__ == "__main__":
    test_batch_parser()
