import json
from .index_use import IndexRead


class PgReadQueryPlan:
    def __init__(self, plan_json):
        self.act_elapsed_max = plan_json.get("Actual Total Time", 0)
        self.est_elapsed_time = plan_json.get("Total Cost", 0)
        self.est_cpu_time = 0
        self.act_cpu_sum = 0  # Not available in PG plans

        self.non_clustered_index_usages = {}
        self.clustered_index_usages = {}
        self.clustered_view_usages = {}
        self.non_clustered_view_usages = {}

        self.sub_tree_cost = plan_json.get("Total Cost", 0)
        self.total_sub_tree_cost = plan_json.get("Total Cost", 0)
        self.total_actual_elapsed_max = self.act_elapsed_max
        self.total_actual_elapsed_sum = self.act_elapsed_max

        self._traverse(plan_json)

    def _traverse(self, node):
        node_type = node.get("Node Type", "")
        index_name = node.get("Index Name")
        table_name = node.get("Relation Name")

        if node_type in ["Index Scan", "Index Only Scan", "Bitmap Index Scan"] and index_name and table_name:
            index_use = IndexRead(
                node_id=id(node),
                table=table_name,
                index=index_name,
                index_kind="BTREE",
                act_elapsed_max=node.get("Actual Total Time", 0),
                act_elapsed_sum=node.get("Actual Total Time", 0),
                est_elapsed=node.get("Total Cost", 0),
                act_cpu_max=0,
                act_cpu_sum=0,
                est_cpu=0,
                sub_tree_cost=node.get("Total Cost", 0),
                act_rows_read=node.get("Actual Rows", 0),
                act_rows_output=node.get("Actual Rows", 0),
                est_rows_output=node.get("Plan Rows", 0),
                est_rows_read=node.get("Plan Rows", 0),
                table_cardinality=0
            )
            self.non_clustered_index_usages[id(node)] = index_use
            print(f"[INFO] {node_type} on table {table_name} using index {index_name}")

        elif node_type == "Seq Scan" and table_name:
            print(f"[INFO] Seq Scan on table {table_name} (no index used)")

        for child in node.get("Plans", []):
            self._traverse(child)

    def __getitem__(self, key):
        return self.__dict__[key]

    def get_all_index_reads(self):
        return list(self.non_clustered_index_usages.values()) + list(self.clustered_index_usages.values())
