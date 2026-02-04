# schema_loader.py
from pathlib import Path
from collections import defaultdict
import re

def parse_schema_from_ddl(ddl_text):
    schema = defaultdict(set)
    current_table = None
    for line in ddl_text.splitlines():
        line = line.strip().rstrip(',')
        if line.lower().startswith("create table"):
            match = re.search(r"create table (\w+)", line, re.IGNORECASE)
            if match:
                current_table = match.group(1).lower()
        elif current_table and line and not line.lower().startswith("primary"):
            parts = line.split()
            if len(parts) >= 2:
                column_name = parts[0].lower()
                schema[current_table].add(column_name)
    return dict(schema)


def load_schema_from_ddl_file(path: str):
    ddl_text = Path(path).read_text(encoding="utf-8")
    raw_schema = parse_schema_from_ddl(ddl_text)
    normalized = {
        table: {col for col in cols}
        for table, cols in raw_schema.items()
    }
    return normalized
