import constants
import logging

def bulk_create(db, schema_name, bandit_arm_list):
        """
            This uses create_index method to create multiple indexes at once. This is used when a super arm is pulled

            :param connection: sql_connection
            :param schema_name: name of the database schema
            :param bandit_arm_list: list of BanditArm objects
            :return: cost (regret)
        """
        cost = {}
        for name, bandit_arm in bandit_arm_list.items():
            if type(bandit_arm).__name__ == 'BanditArmMV':
                cost[name] = db.create_view(bandit_arm.index_name, bandit_arm.view_query,
                                        bandit_arm.index_query)
                if cost[name]:
                    bandit_arm.memory = db.get_arm_size_mv(bandit_arm.index_name)
            else:
                cost[name] = db.create_index(bandit_arm.table_name, bandit_arm.index_cols,
                                            bandit_arm.index_name,
                                            bandit_arm.include_cols, schema_name)
                bandit_arm.memory = db.get_arm_size(bandit_arm.index_name)
        return cost


def bulk_drop(db, schema_name, bandit_arm_list, file=None):
    """
    Drops the index for all given bandit arms

    :param connection: sql_connection
    :param schema_name: name of the database schema
    :param bandit_arm_list: list of bandit arms
    :return:
    """
    for name, bandit_arm in bandit_arm_list.items():
        if type(bandit_arm).__name__ == 'BanditArmMV':
            db.drop_view(name)
        else:
            db.drop_index(bandit_arm.index_name)


def create_query_v7(db, schema_name, arm_list_to_add, arm_list_to_delete, queries):
    """
    This method aggregate few functions of the sql helper class.
        1. This method create the indexes related to the given bandit arms
        2. Execute all the queries in the given list
        3. Clean (drop) the created indexes
        4. Finally returns the cost taken to run all the queries

    :param connection: sql_connection
    :param schema_name: name of the database schema
    :param arm_list_to_add: arms that need to be added in this round
    :param arm_list_to_delete: arms that need to be removed in this round
    :param queries: queries that should be executed
    :return:
    """
    db.get_tables()
    creation_cost = bulk_create(db, schema_name, arm_list_to_add)
    execute_cost = 0
    execute_cost_transactional = 0
    execute_cost_analytical = 0
    query_plans = []
    query_times = {}
    query_counts = {}
    is_analytical = {}
    for query in queries:
        query_plan = db.execute_query_v2(query.get_query_string())
        if query_plan:
            cost = query_plan[constants.COST_TYPE_CURRENT_EXECUTION]
            if query.id in query_times:
                query_times[query.id] += cost
                query_counts[query.id] += 1
            else:
                query_times[query.id] = cost
                query_counts[query.id] = 1
                is_analytical[query.id] = query.is_analytical
            execute_cost += cost
            if query.is_analytical:
                execute_cost_analytical += cost
            else:
                execute_cost_transactional += cost
            if query.first_seen == query.last_seen:
                query.original_running_time = cost

        query_plans.append(query_plan)

    for q_id, q_time in query_times.items():
        logging.info(f"Query {q_id}: \tanalytical-{is_analytical[q_id]} \tcount-{query_counts[q_id]} \tcost-{q_time}")
    logging.info(f"Index creation cost: {sum(creation_cost.values())}")
    logging.info(f"Time taken to run the queries: {execute_cost}")
    logging.info(f"Time taken for analytical queries: {execute_cost_analytical}")
    logging.info(f"Time taken for transactional queries: {execute_cost_transactional}")

    return execute_cost, creation_cost, query_plans, execute_cost_analytical, execute_cost_transactional


def hyp_bulk_create(db, schema_name, bandit_arm_list, file):
    """
        This uses create_index method to create multiple indexes at once. This is used when a super arm is pulled

        :param connection: sql_connection
        :param schema_name: name of the database schema
        :param bandit_arm_list: list of BanditArm objects
        :return: cost (regret)
    """
    cost = 0
    for name, bandit_arm in bandit_arm_list.items():
        if type(bandit_arm).__name__ == 'BanditArmMV':
            cost += db.hyp_create_view(bandit_arm.index_name, bandit_arm.view_query,
                                        bandit_arm.index_query, file)
        else:
            cost += db.hyp_create_index_v1(schema_name, bandit_arm.table_name, bandit_arm.index_cols,
                                            bandit_arm.index_name, file, bandit_arm.include_cols)
    return cost


def hyp_check_config(db, schema_name, arm_list_to_add, queries, file_path):
        """
        This method aggregate few functions of the sql helper class.
            1. This method create the indexes related to the given bandit arms
            2. Execute all the queries in the given list
            3. Clean (drop) the created indexes
            4. Finally returns the time taken to run all the queries

        :param arm_list_to_add: new arms considered in this round
        :param super_arm_list: complete arm list
        :param queries: queries that should be executed
        :return:
        """
        cost = 0
        file = open(file_path, 'w')
        db.get_tables()
        cost += hyp_bulk_create(db, schema_name, arm_list_to_add, file)
        query_plans = []
        db.hyp_enable_index(file)
        for query in queries:
            query_plan, exe_cost = db.hyp_execute_query_v2(query.get_query_string(hyp=True), file)
            if query_plan:
                query_plans.append(query_plan)
                cost += exe_cost
                if query.first_seen == query.last_seen:
                    query.original_hyp_running_time = query_plan.sub_tree_cost
            else:
                print(f"[ERROR] query_plan is none:")
        bulk_drop(db, schema_name, arm_list_to_add, file)
        file.close()

        return query_plans, cost



def get_estimated_size_of_index_v1(db, schema_name, tbl_name, col_names):
    """
    This helper method can be used to get a estimate size for a index. This simply multiply the column sizes with a
    estimated row count (need to improve further)

    :param connection: sql_connection
    :param schema_name: name of the database schema
    :param tbl_name: name of the database table
    :param col_names: string list of column names
    :return: estimated size in MB
    """
    table = db.get_tables()[tbl_name]
    primary_key = db.get_primary_key(tbl_name)
    col_not_pk = tuple(set(col_names) - set(primary_key))
    key_columns_length = get_column_data_length(db, tbl_name, col_not_pk)
    row_count = table.table_row_count
    estimated_size = row_count * key_columns_length
    estimated_size = estimated_size / float(1024*1024)
    return estimated_size


def get_estimated_size_of_mv_v2(db, payload, mv_query, count_query, count_query_id, is_gb):
    """
    This helper method can be used to get a estimate size for a index. This simply multiply the column sizes with a
    estimated row count (need to improve further)

    :param connection: sql_connection
    :param payload: payload of the MV query
    :param mv_query: query used to create the MV
    :return: estimated size in MB
    """
    # Except for the estimated number of rows, rest of the calculation looks accurate.
    # Bit hard to think of a better way to estimate the number of rows
    # estimated_rows = QueryPlan.get_plan(get_query_plan_xml(connection, mv_query)).estimated_rows
    global count_numbers
    global cache_hits
    if count_query_id in count_numbers and not is_gb:
        estimated_rows = count_numbers[count_query_id]
        cache_hits += 1
    else:
        try:
            cursor = db.conn.cursor()
            cursor.execute(count_query)
            result = cursor.fetchone()
            estimated_rows = result[0]
            if not is_gb:
                count_numbers[count_query_id] = estimated_rows
        except:
            if not is_gb:
                count_numbers[count_query_id] = -1
            estimated_rows = -1

    if estimated_rows > 0:
        tables = set(payload.keys())
        total_row_length = 0
        header_size = 4
        nullable_buffer = 2
        for tbl_name in tables:
            columns = set()
            if tbl_name in payload:
                columns = columns.union(payload[tbl_name])
            key_columns_length = get_column_data_length(db, tbl_name, columns)
            total_row_length += key_columns_length

        rows_per_page = 8096/(total_row_length + nullable_buffer + header_size)
        number_of_leafs = estimated_rows/rows_per_page

        return (8192 * number_of_leafs) / float(1024 * 1024)
    else:
        return -1


# TODO test
def get_column_data_length(db, table_name, col_names):
    """
    get the data length of given set of columns
    :param connection: SQL Connection
    :param table_name: Name of the SQL table
    :param col_names: array of columns
    :return:
    """
    tables = db.get_tables()
    # for table_name in tables.keys():
    #     print("table:", tables[table_name])
    varchar_count = 0
    column_data_length = 0
    # TODO find col_names!!!
    # print("col_names:", col_names)

    # for column_name in col_names:
    #     print("column_name:", column_name)

    for column_name in col_names:
        # print(tables[table_name].columns)
        column = tables[table_name].columns[column_name]
        if column.column_type == 'varchar':
            varchar_count += 1
        column_data_length += column.column_size if column.column_size else 0

    if varchar_count > 0:
        variable_key_overhead = 2 + varchar_count * 2
        return column_data_length + variable_key_overhead
    else:
        return column_data_length