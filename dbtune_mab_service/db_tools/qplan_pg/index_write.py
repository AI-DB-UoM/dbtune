import json
from .index_use import IndexWrite 
class PgWriteQueryPlan:

    def __init__(self, plan_json: dict, po_set: set):
        self.po_set = po_set
        self.plan = plan_json["Plan"]
        self.index_writes = self._extract_index_uses(self.plan)

    def _extract_index_uses(self, node, index_uses=None):
        if index_uses is None:
            index_uses = []

        node_type = node.get("Node Type", "")
        index_name = node.get("Index Name")
        table_name = node.get("Relation Name")

        if node_type in self.po_set and index_name and table_name:
            index_use = IndexWrite(
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
                act_rows_output=node.get("Actual Rows", 0),
                est_rows_output=node.get("Plan Rows", 0)
            )
            index_uses.append(index_use)

        for child in node.get("Plans", []):
            self._extract_index_uses(child, index_uses)

        return index_uses


class PgInsertQueryPlan(PgWriteQueryPlan):
    def __init__(self, plan_json):
        super().__init__(plan_json, po_set={"Insert"})


class PgDeleteQueryPlan(PgWriteQueryPlan):
    def __init__(self, plan_json):
        super().__init__(plan_json, po_set={"Delete"})


class PgUpdateQueryPlan(PgWriteQueryPlan):
    def __init__(self, plan_json):
        super().__init__(plan_json, po_set={"Update"})
