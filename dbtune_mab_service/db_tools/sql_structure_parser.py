import sqlglot
from collections import defaultdict
import re
import json

TPC_SCHEMA = {
    "store": {
        "s_store_sk", "s_store_id", "s_rec_start_date", "s_rec_end_date", "s_closed_date_sk",
        "s_store_name", "s_number_employees", "s_floor_space", "s_hours", "s_manager",
        "s_market_id", "s_geography_class", "s_market_desc", "s_market_manager",
        "s_division_id", "s_division_name", "s_company_id", "s_company_name",
        "s_street_number", "s_street_name", "s_street_type", "s_suite_number",
        "s_city", "s_county", "s_state", "s_zip", "s_country",
        "s_gmt_offset", "s_tax_precentage"
    },
    "store_returns": {
        "sr_returned_date_sk", "sr_return_time_sk", "sr_item_sk", "sr_customer_sk",
        "sr_cdemo_sk", "sr_hdemo_sk", "sr_addr_sk", "sr_store_sk", "sr_reason_sk",
        "sr_ticket_number", "sr_return_quantity", "sr_return_amt", "sr_return_tax",
        "sr_return_amt_inc_tax", "sr_fee", "sr_return_ship_cost", "sr_refunded_cash",
        "sr_reversed_charge", "sr_store_credit", "sr_net_loss"
    },
    "customer": {
        "c_customer_sk", "c_customer_id", "c_current_cdemo_sk", "c_current_hdemo_sk",
        "c_current_addr_sk", "c_first_shipto_date_sk", "c_first_sales_date_sk",
        "c_salutation", "c_first_name", "c_last_name", "c_preferred_cust_flag",
        "c_birth_day", "c_birth_month", "c_birth_year", "c_birth_country",
        "c_login", "c_email_address", "c_last_review_date"
    },
    "date_dim": {
        "d_date_sk", "d_date_id", "d_date", "d_month_seq", "d_week_seq", "d_quarter_seq",
        "d_year", "d_dow", "d_moy", "d_dom", "d_qoy", "d_fy_year", "d_fy_quarter_seq",
        "d_fy_week_seq", "d_day_name", "d_quarter_name", "d_holiday", "d_weekend",
        "d_following_holiday", "d_first_dom", "d_last_dom", "d_same_day_ly", "d_same_day_lq",
        "d_current_day", "d_current_week", "d_current_month", "d_current_quarter",
        "d_current_year"
    }
}

NORMALIZED_SCHEMA = {
    t.lower(): {col.lower() for col in cols} for t, cols in TPC_SCHEMA.items()
}

def parse_schema_from_ddl(ddl_text):
    schema = defaultdict(set)
    current_table = None
    for line in ddl_text.splitlines():
        line = line.strip().rstrip(',')
        if line.lower().startswith("create table"):
            match = re.search(r"create table (\w+)", line, re.IGNORECASE)
            if match:
                current_table = match.group(1).lower()
        elif current_table and line and not line.startswith("primary"):
            parts = line.split()
            if len(parts) >= 2:
                column_name = parts[0].lower()
                schema[current_table].add(column_name)
    return dict(schema)

# TODO:
# Queries with no filter condition (i.e., no predicates) may result in empty predicate maps.
# These cases include:
# - SELECT * FROM table LIMIT 10 -- no WHERE clause
# - SELECT col1, col2 FROM t1 JOIN t2 ON t1.id = t2.id -- structural join, no filters
# - SELECT col FROM t -- simple scan without conditions
# In such cases, the query might not require tuning or index optimization.

class SQLStructureParser:
    def __init__(self, query, query_id=1, schema=None):
        self.query = query
        self.query_id = query_id
        self.schema = schema or NORMALIZED_SCHEMA
        self.ast = sqlglot.parse_one(query, read='postgres')
        self.alias_map = self._extract_alias_map()

    def _extract_alias_map(self):
        alias_map = {}
        for node in self.ast.find_all(sqlglot.expressions.Alias):
            if isinstance(node.this, sqlglot.expressions.Column):
                alias_map[node.alias.lower()] = node.this.name.lower()
        return alias_map

    def _resolve_column(self, table, column):
        col_key = column.lower()
        original_col = self.alias_map.get(col_key, col_key)
        if table:
            return table.lower(), original_col
        candidates = [t for t, cols in self.schema.items() if original_col in cols]
        if len(candidates) == 1:
            return candidates[0], original_col
        return "unknown", original_col

    def _filter_by_schema(self, mapping):
        return {k: sorted(v) for k, v in mapping.items() if k in self.schema}

    def extract_tables_and_columns(self):
        result = defaultdict(set)
        for col in self.ast.find_all(sqlglot.expressions.Column):
            tbl, colname = self._resolve_column(col.table, col.name)
            result[tbl].add(colname)
        return result

    def extract_predicates(self):
        result = defaultdict(set)
        for cond in self.ast.find_all(sqlglot.expressions.Condition):
            for col in cond.find_all(sqlglot.expressions.Column):
                tbl, colname = self._resolve_column(col.table, col.name)
                result[tbl].add(colname)
        return result

    def extract_group_by(self):
        result = defaultdict(set)
        group = self.ast.args.get("group")
        if group:
            for col in group.expressions:
                if isinstance(col, sqlglot.expressions.Column):
                    tbl, colname = self._resolve_column(col.table, col.name)
                    result[tbl].add(colname)
        return result

    def extract_order_by(self):
        result = defaultdict(set)
        order = self.ast.args.get("order")
        if order:
            for ob in order.expressions:
                col = ob.this
                if isinstance(col, sqlglot.expressions.Column):
                    tbl, colname = self._resolve_column(col.table, col.name)
                    result[tbl].add(colname)
        return result
    
    def extract_joins(self):
        """
        Extract join conditions between tables:
        Returns:
            {
                ("table1", "table2"): [("col1", "col2"), ...]
            }
        """
        joins = defaultdict(list)
        for join in self.ast.find_all(sqlglot.expressions.Join):
            on_expr = join.args.get("on")
            if not on_expr:
                continue

            for condition in on_expr.find_all(sqlglot.expressions.EQ):
                left = condition.args.get("this")
                right = condition.args.get("expression")

                if isinstance(left, sqlglot.expressions.Column) and isinstance(right, sqlglot.expressions.Column):
                    tbl1, col1 = self._resolve_column(left.table, left.name)
                    tbl2, col2 = self._resolve_column(right.table, right.name)
                    key = tuple(sorted([tbl1, tbl2]))
                    joins[key].append((col1, col2))
        return dict(joins)

    def to_dict(self):
        raw_predicates = self.extract_predicates()
        raw_payload = self.extract_tables_and_columns()
        raw_group_by = self.extract_group_by()
        raw_order_by = self.extract_order_by()
        raw_joins = self.extract_joins()

        return {
            "id": self.query_id,
            "query_string": self.query,
            "raw_predicates": {k: sorted(v) for k, v in raw_predicates.items()},
            "raw_payload": {k: sorted(v) for k, v in raw_payload.items()},
            "raw_group_by": {k: sorted(v) for k, v in raw_group_by.items()},
            "raw_order_by": {k: sorted(v) for k, v in raw_order_by.items()},
            "predicates": self._filter_by_schema(raw_predicates),
            "payload": self._filter_by_schema(raw_payload),
            "group_by": self._filter_by_schema(raw_group_by),
            "order_by": self._filter_by_schema(raw_order_by),
            "joins": raw_joins,
        }

    def print_structure(self):
        structure = self.to_dict()
        print(json.dumps(structure, indent=2))
