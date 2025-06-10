import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_tools.query_loader import QueryLoader

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WORKLOAD_DIR = os.path.join(BASE_DIR, "workloads")

def test_load_csv():
    path = os.path.join(WORKLOAD_DIR, "test_workload.csv")
    queries = QueryLoader.load_from_csv(path)
    print("CSV Queries:", queries)

def test_load_sql():
    path = os.path.join(WORKLOAD_DIR, "test_workload.sql")
    queries = QueryLoader.load_from_sql(path)
    print("SQL Queries:", queries)

def test_load_txt():
    path = os.path.join(WORKLOAD_DIR, "test_workload.txt")
    queries = QueryLoader.load_from_txt(path)
    print("TXT Queries:", queries)

if __name__ == "__main__":
    test_load_csv()
    test_load_sql()
    test_load_txt()
