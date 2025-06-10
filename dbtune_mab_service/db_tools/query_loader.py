# query_loader.py
import csv
import os

        
from fastapi import HTTPException
from pathlib import Path
import requests

class QueryLoader:
    @staticmethod
    def load_from_csv(filepath):
        queries = []
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'query' in row:
                    queries.append(row['query'].strip())
        return queries

    @staticmethod
    def load_from_sql(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Split on ';' and remove empty queries
            return [q.strip() + ';' for q in content.split(';') if q.strip()]

    @staticmethod
    def load_from_txt(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    @staticmethod
    def load_query_workloads(options):

        queries = None
        if "query_file" in options:
            try:
                with open(Path(options["query_file"])) as f:
                    queries = f.read()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read query_file: {e}")
        elif "query_url" in options:
            try:
                r = requests.get(options["query_url"], timeout=5)
                r.raise_for_status()
                queries = r.text
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to fetch query_url: {e}")

        return queries
