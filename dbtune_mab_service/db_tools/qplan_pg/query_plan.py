import json
import constants

from .index_read import PgReadQueryPlan
from .index_write import PgInsertQueryPlan, PgUpdateQueryPlan, PgDeleteQueryPlan


class QueryPlan:

    @staticmethod
    def get_plan(pg_plan_json_str, query_str):
        """
        Parse PostgreSQL EXPLAIN JSON output into a PgQueryPlan object
        """
        pg_plan_json = json.loads(pg_plan_json_str)
        plan_root = pg_plan_json[0].get("Plan", {})

        # stmt_text = pg_plan_json[0].get("Query Text", "").lower()

        if query_str.startswith("select") or query_str.startswith("with"):
            return PgReadQueryPlan(plan_root)
        elif query_str.startswith("insert"):
            return PgInsertQueryPlan(plan_root)
        elif query_str.startswith("delete"):
            return PgDeleteQueryPlan(plan_root)
        elif query_str.startswith("update"):
            return PgUpdateQueryPlan(plan_root)
        else:
            raise ValueError("Unsupported statement type")



    # @staticmethod
    # def get_plan(plan_json):
    #     plan_data = json.loads(plan_json)[0]
    #     print(plan_data)
    #     return QueryPlan._traverse_plan(plan_data['Plan'])

    # @staticmethod
    # def _traverse_plan(node, index_uses=None):
    #     if index_uses is None:
    #         index_uses = []

    #     node_type = node.get("Node Type", "")
    #     index_name = node.get("Index Name")
    #     table_name = node.get("Relation Name")

    #     node_id = id(node)
    #     act_elapsed = node.get("Actual Total Time", 0)
    #     act_rows_output = node.get("Actual Rows", 0)
    #     est_rows_output = node.get("Plan Rows", 0)
    #     cost = node.get("Total Cost", 0)

    #     if node_type in ["Index Scan", "Index Only Scan", "Bitmap Index Scan"] and index_name and table_name:
    #         index_use = PgIndexRead(
    #             node_id=node_id,
    #             table=table_name,
    #             index=index_name,
    #             index_kind="BTREE",
    #             act_elapsed_max=act_elapsed,
    #             act_elapsed_sum=act_elapsed,
    #             est_elapsed=cost,
    #             act_cpu_max=0,
    #             act_cpu_sum=0,
    #             est_cpu=0,
    #             sub_tree_cost=cost,
    #             act_rows_read=act_rows_output,
    #             act_rows_output=act_rows_output,
    #             est_rows_output=est_rows_output,
    #             est_rows_read=est_rows_output,
    #             table_cardinality=0
    #         )
    #         index_uses.append(index_use)
        
    #     elif node_type == "Seq Scan" and table_name:
    #         print(f"[INFO] Seq Scan detected on table '{table_name}', no index used.")

    #     elif node_type in ["Insert", "Update", "Delete"] and index_name and table_name:
    #         index_use = PgIndexWrite(
    #             node_id=node_id,
    #             table=table_name,
    #             index=index_name,
    #             index_kind="BTREE",
    #             act_elapsed_max=act_elapsed,
    #             act_elapsed_sum=act_elapsed,
    #             est_elapsed=cost,
    #             act_cpu_max=0,
    #             act_cpu_sum=0,
    #             est_cpu=0,
    #             sub_tree_cost=cost,
    #             act_rows_output=act_rows_output,
    #             est_rows_output=est_rows_output
    #         )
    #         index_uses.append(index_use)

    #     if "Plans" in node:
    #         for sub_node in node["Plans"]:
    #             QueryPlan._traverse_plan(sub_node, index_uses)

    #     return index_uses