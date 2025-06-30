
import logging
import os
import datetime
import numpy
import copy
import sys
import time

import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_tools.postgres_db import PostgresDB
from db_tools.db_bandit_helper import bulk_create, bulk_drop, create_query_v7, hyp_check_config
from db_tools.sql_structure_parser import SQLStructureParser
from db_tools.query_loader import QueryLoader
from db_tools.query import Query
from bandits.oracle_MV import OracleV1 as OracleMV
from bandits.oracle_super import OracleV1 as OracleS
from bandits.oracle import OracleV1 as Oracle
import bandits.bandit_helper as bandit_helper
import constants
import bandits.bandit_c2ucb as bandits


class BanditTuner:

    def get_db_config(self):
        return {
            "dbname": "pgdb",
            "user": "pguser",
            "password": "123456",
            "host": "aidb-postgres-1",
            "port": 5432
        }
        # return {
        #     "dbname": "pgdb",
        #     "user": "pguser",
        #     "password": "123456",
        #     "host": "localhost",
        #     "port": 5438
        # }

    def __init__(self):
        # configuring the logger
        logging.basicConfig(
            filename=os.path.join(constants.LOG_PATH, 'test.log'),
            filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
        logging.getLogger().setLevel(logging.DEBUG)

        self.enable_tune = True
        self.with_mv = True
        self.mv = 'MV'
        constants.max_memory = 25000 # TODO max_memory is from configs
        self.max_memory = constants.max_memory

        self.db = PostgresDB(self.get_db_config())
        self.db.connect()

        # get all tables
        self.tables = self.db.get_tables()

        # TODO reset hyp query log
        # hyp_file_path = os.path.join(helper.get_experiment_folder_path(configs.experiment_id), configs.experiment_id + '_hyp.sql')
        self.hyp_file = "./hyp_files/temp.txt"

        self.init_queries()

        # TODO Get all the columns from the database
        self.bandits_dict = {}
        self.columns = {}
        self.column_counts = {}
        self.max_memory -= self.db.get_current_pds_size()
        self.cluster_id = 1
        self.super_static_context_size = 2
        self.hyp_check_rounds = 25
        self.rounds = 25

    def _create_bandits_for_tables(self):
        # Creating bandits for tables
        for table_name in self.candidate_tables:
            self.columns[table_name] = self.db.get_columns_for_table(table_name)
            self.column_counts[table_name] = len(self.columns[table_name])
            context_size = self.column_counts[table_name] * (
                    1 + constants.CONTEXT_UNIQUENESS + constants.CONTEXT_INCLUDES) + constants.STATIC_CONTEXT_SIZE

            # Create oracle and the bandit
            oracle = Oracle(self.max_memory)
            self.bandits_dict[table_name] = bandits.C3UCB(context_size, constants.input_alpha, constants.input_lambda, oracle,
                                                     self.cluster_id)
            self.cluster_id += 1

    def _create_bandits_for_MV(self):
        if self.with_mv:
            # Creating bandit for MVs
            context_size = self.number_of_columns + len(self.tables) + 4
            self.bandits_dict[self.mv] = bandits.C3UCB(context_size, constants.input_alpha, constants.input_lambda,
                                             OracleMV(self.max_memory), self.cluster_id)
            self.cluster_id += 1

    def _create_super_bandit(self):
        oracle_s = OracleS(self.max_memory)
        self.super_bandit = bandits.C3UCB(self.cluster_id + self.super_static_context_size, constants.input_alpha, 
                                     constants.input_lambda, oracle_s)

    def create_bandits(self):
        self._create_bandits_for_tables()
        self._create_bandits_for_MV()
        self._create_super_bandit()

    def init_queries(self, raw_queries: list[str] = [], sql_trainingset: str = "test_workload.sql"):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        filepath = os.path.join(base_dir, "workloads", sql_trainingset)

        if not raw_queries:
            return
            # raw_queries = QueryLoader.load_from_sql(filepath)

        self.query_properties = [
            SQLStructureParser(q, i).to_dict()
            for i, q in enumerate(raw_queries)
        ]

        self.query_obj_store = {}
        self.queries = []

        for i, query in enumerate(raw_queries):
            parsed = SQLStructureParser(query, i).to_dict()
            query_obj = Query(
                query_id=i,
                query_string=query,
                predicates=parsed["predicates"],
                payloads=parsed["payload"]
            )
            query_obj.init_scan_time(self.tables.keys())
            self.queries.append(query_obj)

        self.candidate_tables = [
            table for table in self.tables
            if self.db.get_table_row_count(table) >= constants.SMALL_TABLE_IGNORE
        ]

        self.all_columns, self.number_of_columns = self.db.get_all_columns()

    def train_MAB_via_dead_loop(self):

        results = []
        # hyp_check_rounds = 25
        super_static_context_size = 2
        arm_selection_count = {}
        chosen_arms_last_round = {}

        self.create_bandits()

        number_of_clusters = self.cluster_id

        total_time = 0.0

        # self.rounds = 30
        self.current_round = 0
        current_round = 0
        # for t in range(self.rounds):
        while True:
            if not self.enable_tune:
                time.sleep(2)
                continue

            if self.current_round >= self.rounds:
                logging.info("Reached max rounds. Ignoring tune signal.")
                self.enable_tune = False
                time.sleep(2)
                continue
            
            # print(f"round: {t}")
            logging.info(f"----------------round: {self.current_round}----------------")
            self.current_round += 1
            start_time_round = datetime.datetime.now()
            # TODO  update queries_start and queries_end
            queries_start = 0
            queries_end = 10
            queries_current_batch = self.queries[queries_start : queries_end]

            # print("queries_current_batch", queries_current_batch[0])
            query_obj_list_current = []
            for query in queries_current_batch:
                if query.id in self.query_obj_store:
                    query_obj_in_store = self.query_obj_store[query.id]
                    query_obj_in_store.frequency += 1
                    query_obj_in_store.last_seen = self.current_round
                    query_obj_in_store.query_strings.append(query.query_string)
                    if query_obj_in_store.first_seen == -1:
                        query_obj_in_store.first_seen = self.current_round
                else:
                    query_copy = copy.deepcopy(query)
                    self.query_obj_store[query.id] = query_copy
                query_obj_list_current.append(self.query_obj_store[query.id])
            # This list contains all past queries, we don't include new queries seen for the first time.

            query_obj_list_past = []
            query_obj_list_new = []

            # print("self.query_obj_store", self.query_obj_store)
            for key, obj in self.query_obj_store.items():
                if self.current_round == 0:
                    query_obj_list_past.append(obj)
                else:
                    if self.current_round - obj.last_seen <= constants.QUERY_MEMORY and 0 <= obj.first_seen < current_round:
                        query_obj_list_past.append(obj)
                    elif self.current_round - obj.last_seen > constants.QUERY_MEMORY:
                        obj.first_seen = -1
                    elif obj.first_seen == self.current_round:
                        query_obj_list_new.append(obj)

            # We don't want to reset in the first round, if there is new additions or removals we identify a
            # workload change
            if self.current_round > 0 and len(query_obj_additions) > 0:
                workload_change = len(query_obj_additions) / len(query_obj_list_past)
                for table_name in self.candidate_tables:
                    self.bandits_dict[table_name].workload_change_trigger(workload_change)
                if self.with_mv:
                    self.bandits_dict[self.mv].workload_change_trigger(workload_change)

            # this rounds new will be the additions for the next round
            query_obj_additions = query_obj_list_new

            # Get the predicates, frequent table subsets for queries and Generate index and view arms for each query
            index_arms = {}
            frequent_table_subsets = {}
            if self.with_mv:
                frequent_table_subsets = bandit_helper.gen_frq_table_subsets(query_obj_list_past, self.tables,
                                                                             self.query_properties)
            for i in range(len(query_obj_list_past)):
                bandit_arms_tmp = bandit_helper.gen_arms_from_predicates_v2(self.db, query_obj_list_past[i])
                bandit_arms_mv = {}
                # print("with_mv", self.with_mv)
                if self.with_mv:
                    bandit_arms_mv = bandit_helper.gen_mv_arms_from_predicates_v3(self.db, query_obj_list_past[i],
                                                                                  self.tables, frequent_table_subsets,
                                                                                  self.query_properties, True)
                    # bandit_arms_mv = bandit_helper.finalizing_mv_arms(self.connection, bandit_arms_mv)
                # Adding index arms
                    # print("bandit_arms_mv", bandit_arms_mv)
                for key, index_arm in bandit_arms_tmp.items():
                    table_name = index_arm.table_name
                    if table_name not in index_arms:
                        index_arms[table_name] = {}
                    if key not in index_arms[table_name]:
                        index_arm.query_ids = set()
                        index_arm.query_ids_backup = set()
                        index_arm.clustered_index_time = 1
                        index_arms[table_name][key] = index_arm
                    # index_arm.clustered_index_time += max(
                    #     query_obj_list_past[i].table_scan_times[index_arm.table_name]) if \
                    #     query_obj_list_past[i].table_scan_times[index_arm.table_name] else 0
                    index_arm.clustered_index_time += query_obj_list_past[i].original_running_time
                    index_arms[table_name][key].query_ids.add(index_arm.query_id)
                    index_arms[table_name][key].query_ids_backup.add(index_arm.query_id)

                if self.with_mv:
                    # Adding MV arms
                    for key, index_arm in bandit_arms_mv.items():
                        table_name = index_arm.table_name
                        if table_name not in index_arms:
                            index_arms[table_name] = {}
                        if key not in index_arms[table_name]:
                            index_arm.query_ids = set()
                            index_arm.query_ids_backup = set()
                            index_arm.clustered_index_time = 1
                            index_arms[table_name][key] = index_arm
                        for ta in index_arm.table_names:
                            index_arm.clustered_index_time += max(
                                query_obj_list_past[i].table_scan_times[ta]) if \
                                query_obj_list_past[i].table_scan_times[ta] else 0
                        index_arms[table_name][key].query_ids.add(index_arm.query_id)
                        index_arms[table_name][key].query_ids_backup.add(index_arm.query_id)

            # set the index arms at the bandit
            if self.mv in index_arms:
                bandit_helper.finalizing_mv_arms(self.db, index_arms[self.mv], self.query_properties, self.max_memory)
            # print("index_arms", index_arms)
            chosen_arms = {}
            chosen_arm_ids = {}
            for table_name in self.candidate_tables:
                index_arms_for_table = {}
                if table_name not in index_arms:
                    continue
                
                index_arms_for_table = index_arms[table_name]

                index_arm_list = list(index_arms_for_table.values())
                logging.info(f"Generated {len(index_arm_list)} arms for table {table_name}")
                # print(f"Generated {len(index_arm_list)} arms for table {table_name}")
                self.bandits_dict[table_name].set_arms(index_arm_list)

                # creating the context, here we pass all the columns in the database
                context_vectors_v1 = bandit_helper.get_name_encode_cv_v2(index_arms_for_table, self.columns[table_name], self.column_counts[table_name], constants.CONTEXT_UNIQUENESS, constants.CONTEXT_INCLUDES)
                context_vectors_v2 = bandit_helper.get_derived_value_cv_v4(self.db, index_arms_for_table, query_obj_list_past, chosen_arms_last_round, constants.INDEX_INCLUDES)

                context_vectors = []
                for i in range(len(context_vectors_v1)):
                    context_vectors.append(
                        numpy.array(list(context_vectors_v2[i]) + list(context_vectors_v1[i]), ndmin=2))
                # getting the super arm from the bandit
                chosen_arm_ids[table_name] = self.bandits_dict[table_name].select_arm(context_vectors, self.current_round)

                # get objects for the chosen set of arm ids
                if chosen_arm_ids[table_name]:
                    for (arm_id, ucb) in chosen_arm_ids[table_name]:
                        index_name = index_arm_list[arm_id].index_name
                        if table_name not in chosen_arms:
                            chosen_arms[table_name] = {}
                        chosen_arms[table_name][index_name] = (index_arm_list[arm_id], arm_id, ucb)
            
            # setting arms for MV bandit
            if self.with_mv:
                index_arm_list = {}
                index_arms_for_table = {}
                if self.mv in index_arms:
                    index_arm_list = list(index_arms[self.mv].values())
                    index_arms_for_table = index_arms[self.mv]

                logging.info(f"Generated {len(index_arm_list)} arms")
                self.bandits_dict[self.mv].set_arms(index_arm_list)

                context_vectors = bandit_helper.get_view_encode_cv_v1(self.db, index_arms_for_table, self.all_columns,
                                                                      self.number_of_columns, chosen_arms_last_round)
                chosen_arm_ids[self.mv] = self.bandits_dict[self.mv].select_arm(context_vectors, self.current_round)
                chosen_arms[self.mv] = {}
                if chosen_arm_ids[self.mv]:
                    for (arm_id, ucb) in chosen_arm_ids[self.mv]:
                        index_name = index_arm_list[arm_id].index_name
                        chosen_arms[self.mv][index_name] = (index_arm_list[arm_id], arm_id, ucb)
        
            super_arm_list, super_context, original_map = bandit_helper.get_super_bandit_context(
                self.db, chosen_arms, chosen_arms_last_round, super_static_context_size, number_of_clusters)
            self.super_bandit.set_arms(super_arm_list)
            super_chosen_arm_ids, mv_size_weight, index_size_weight = self.super_bandit.select_super_arm_v2(super_context)
            super_chosen_per_table = {}
            for c_id in super_chosen_arm_ids:
                c_t, c_aid = original_map[c_id]
                if c_t not in super_chosen_per_table:
                    super_chosen_per_table[c_t] = []
                super_chosen_per_table[c_t].append(c_aid)

            super_chosen_arms = {}
            used_memory = 0
            if super_chosen_arm_ids:
                for arm_id in super_chosen_arm_ids:
                    index_name = super_arm_list[arm_id].index_name
                    super_chosen_arms[index_name] = super_arm_list[arm_id]
                    used_memory = used_memory + super_arm_list[arm_id].memory
                    if index_name in arm_selection_count:
                        arm_selection_count[index_name] += 1
                    else:
                        arm_selection_count[index_name] = 1

            # finding the difference between last round and this round
            keys_last_round = set(chosen_arms_last_round.keys())
            keys_this_round = set(super_chosen_arms.keys())
            key_intersection = keys_last_round & keys_this_round
            key_additions = keys_this_round - key_intersection
            key_deletions = keys_last_round - key_intersection
            logging.info(f"Selected: {keys_this_round}")
            logging.debug(f"Added: {key_additions}")
            logging.debug(f"Removed: {key_deletions}")

            added_arms = {}
            deleted_arms = {}
            for key in key_additions:
                added_arms[key] = super_chosen_arms[key]
            for key in key_deletions:
                deleted_arms[key] = chosen_arms_last_round[key]

            start_time_create_query = datetime.datetime.now()
            bulk_drop(self.db, constants.SCHEMA_NAME, deleted_arms)

            hyp_cost = 0
            useless = set()
            if self.current_round < self.hyp_check_rounds:
                # def hyp_check_config(db, schema_name, arm_list_to_add, queries, file_path):
                hyp_query_plans, _ = hyp_check_config(self.db, constants.SCHEMA_NAME,
                                added_arms, query_obj_list_current, self.hyp_file)
                hyp_cost = self.db.get_hyp_cost(self.hyp_file)
                start_time_hyp_reward = datetime.datetime.now()
                hyp_arm_rewards = bandit_helper.calculate_hyp_reward(query_obj_list_current, hyp_query_plans)
                end_time_hyp_reward = datetime.datetime.now()
                hyp_cost += (end_time_hyp_reward - start_time_hyp_reward).total_seconds()
                useless = set(added_arms.keys()) - set(hyp_arm_rewards.keys())
                for a_id in useless:
                    logging.info(f"Suggestion Removed {a_id}")
                    del added_arms[a_id]
                    del super_chosen_arms[a_id]

            result = create_query_v7(self.db, constants.SCHEMA_NAME, added_arms, deleted_arms, query_obj_list_current)
            execution_cost, creation_costs, query_plans, cost_analytical, cost_transactional = result
            arm_rewards = bandit_helper.calculate_reward(creation_costs, query_obj_list_current, query_plans)
            # if constants.LOG_XML:
            #     helper.log_query_xmls(configs.experiment_id, query_obj_list_current, query_plans, t, constants.COMPONENT_MAB)
            end_time_create_query = datetime.datetime.now()
            creation_cost = sum(creation_costs.values())

            self.super_bandit.update_super_v3(super_chosen_arm_ids, arm_rewards, useless, mv_size_weight, index_size_weight)

            for table_name in self.candidate_tables:
                arm_ids = super_chosen_per_table[table_name] if (table_name in super_chosen_per_table) else []
                self.bandits_dict[table_name].update(arm_ids, arm_rewards, useless, mv_size_weight, index_size_weight)

            if self.with_mv:
                arm_ids = super_chosen_per_table[self.mv] if (self.mv in super_chosen_per_table) else []
                self.bandits_dict[self.mv].update(arm_ids, arm_rewards, useless, mv_size_weight, index_size_weight)


            # keeping track of queries that we saw last time
            chosen_arms_last_round = super_chosen_arms

            if self.current_round == (self.rounds - 1):
                bulk_drop(self.db, constants.SCHEMA_NAME, super_chosen_arms)

            end_time_round = datetime.datetime.now()
            current_config_size = self.db.get_current_pds_size()
            logging.info("Size taken by the config: " + str(current_config_size) + "MB")
            # Adding information to the results array
            actual_round_number = self.current_round
            recommendation_time = (end_time_round - start_time_round).total_seconds() + hyp_cost - (
                        end_time_create_query - start_time_create_query).total_seconds()
            logging.info("Recommendation cost: " + str(recommendation_time) + ", Hyp Component: " + str(hyp_cost))
            total_round_time = creation_cost + execution_cost + recommendation_time
            results.append([actual_round_number, constants.MEASURE_BATCH_TIME, total_round_time])
            results.append([actual_round_number, constants.MEASURE_INDEX_CREATION_COST, creation_cost])
            results.append([actual_round_number, constants.MEASURE_QUERY_EXECUTION_COST, execution_cost])
            results.append(
                [actual_round_number, constants.MEASURE_INDEX_RECOMMENDATION_COST, recommendation_time])
            results.append([actual_round_number, constants.MEASURE_MEMORY_COST, current_config_size])
            results.append([actual_round_number, constants.MEASURE_ANALYTICAL_EXECUTION_COST, cost_analytical])
            results.append([actual_round_number, constants.MEASURE_TRANSACTIONAL_EXECUTION_COST, cost_transactional])

            total_time += total_round_time

            print(f"current total {self.current_round}: ", total_time, ", this round: ", total_round_time)
            logging.info(f"current total {self.current_round}: {total_time}, this round: {total_round_time}")

    def train_MAB(self):

        results = []
        hyp_check_rounds = 25
        super_static_context_size = 2
        arm_selection_count = {}
        chosen_arms_last_round = {}

        self.create_bandits()

        number_of_clusters = self.cluster_id

        total_time = 0.0

        # self.rounds = 30

        for t in range(self.rounds):
            # print(f"round: {t}")
            logging.info(f"----------------round: {t}----------------")
            start_time_round = datetime.datetime.now()
            # TODO  update queries_start and queries_end
            queries_start = 0
            queries_end = 10
            queries_current_batch = self.queries[queries_start : queries_end]

            # print("queries_current_batch", queries_current_batch[0])
            query_obj_list_current = []
            for query in queries_current_batch:
                if query.id in self.query_obj_store:
                    query_obj_in_store = self.query_obj_store[query.id]
                    query_obj_in_store.frequency += 1
                    query_obj_in_store.last_seen = t
                    query_obj_in_store.query_strings.append(query.query_string)
                    if query_obj_in_store.first_seen == -1:
                        query_obj_in_store.first_seen = t
                else:
                    query_copy = copy.deepcopy(query)
                    self.query_obj_store[query.id] = query_copy
                query_obj_list_current.append(self.query_obj_store[query.id])
            # This list contains all past queries, we don't include new queries seen for the first time.

            query_obj_list_past = []
            query_obj_list_new = []

            # print("self.query_obj_store", self.query_obj_store)
            for key, obj in self.query_obj_store.items():
                if t == 0:
                    query_obj_list_past.append(obj)
                else:
                    if t - obj.last_seen <= constants.QUERY_MEMORY and 0 <= obj.first_seen < t:
                        query_obj_list_past.append(obj)
                    elif t - obj.last_seen > constants.QUERY_MEMORY:
                        obj.first_seen = -1
                    elif obj.first_seen == t:
                        query_obj_list_new.append(obj)

            # We don't want to reset in the first round, if there is new additions or removals we identify a
            # workload change
            if t > 0 and len(query_obj_additions) > 0:
                workload_change = len(query_obj_additions) / len(query_obj_list_past)
                for table_name in self.candidate_tables:
                    self.bandits_dict[table_name].workload_change_trigger(workload_change)
                if self.with_mv:
                    self.bandits_dict[self.mv].workload_change_trigger(workload_change)

            # this rounds new will be the additions for the next round
            query_obj_additions = query_obj_list_new

            # Get the predicates, frequent table subsets for queries and Generate index and view arms for each query
            index_arms = {}
            frequent_table_subsets = {}
            if self.with_mv:
                frequent_table_subsets = bandit_helper.gen_frq_table_subsets(query_obj_list_past, self.tables,
                                                                             self.query_properties)
            for i in range(len(query_obj_list_past)):
                bandit_arms_tmp = bandit_helper.gen_arms_from_predicates_v2(self.db, query_obj_list_past[i])
                bandit_arms_mv = {}
                # print("with_mv", self.with_mv)
                if self.with_mv:
                    bandit_arms_mv = bandit_helper.gen_mv_arms_from_predicates_v3(self.db, query_obj_list_past[i],
                                                                                  self.tables, frequent_table_subsets,
                                                                                  self.query_properties, True)
                    # bandit_arms_mv = bandit_helper.finalizing_mv_arms(self.connection, bandit_arms_mv)
                # Adding index arms
                    # print("bandit_arms_mv", bandit_arms_mv)
                for key, index_arm in bandit_arms_tmp.items():
                    table_name = index_arm.table_name
                    if table_name not in index_arms:
                        index_arms[table_name] = {}
                    if key not in index_arms[table_name]:
                        index_arm.query_ids = set()
                        index_arm.query_ids_backup = set()
                        index_arm.clustered_index_time = 1
                        index_arms[table_name][key] = index_arm
                    # index_arm.clustered_index_time += max(
                    #     query_obj_list_past[i].table_scan_times[index_arm.table_name]) if \
                    #     query_obj_list_past[i].table_scan_times[index_arm.table_name] else 0
                    index_arm.clustered_index_time += query_obj_list_past[i].original_running_time
                    index_arms[table_name][key].query_ids.add(index_arm.query_id)
                    index_arms[table_name][key].query_ids_backup.add(index_arm.query_id)

                if self.with_mv:
                    # Adding MV arms
                    for key, index_arm in bandit_arms_mv.items():
                        table_name = index_arm.table_name
                        if table_name not in index_arms:
                            index_arms[table_name] = {}
                        if key not in index_arms[table_name]:
                            index_arm.query_ids = set()
                            index_arm.query_ids_backup = set()
                            index_arm.clustered_index_time = 1
                            index_arms[table_name][key] = index_arm
                        for ta in index_arm.table_names:
                            index_arm.clustered_index_time += max(
                                query_obj_list_past[i].table_scan_times[ta]) if \
                                query_obj_list_past[i].table_scan_times[ta] else 0
                        index_arms[table_name][key].query_ids.add(index_arm.query_id)
                        index_arms[table_name][key].query_ids_backup.add(index_arm.query_id)

            # set the index arms at the bandit
            if self.mv in index_arms:
                bandit_helper.finalizing_mv_arms(self.db, index_arms[self.mv], self.query_properties, self.max_memory)
            # print("index_arms", index_arms)
            chosen_arms = {}
            chosen_arm_ids = {}
            for table_name in self.candidate_tables:
                index_arms_for_table = {}
                if table_name not in index_arms:
                    continue
                
                index_arms_for_table = index_arms[table_name]

                index_arm_list = list(index_arms_for_table.values())
                logging.info(f"Generated {len(index_arm_list)} arms for table {table_name}")
                # print(f"Generated {len(index_arm_list)} arms for table {table_name}")
                self.bandits_dict[table_name].set_arms(index_arm_list)

                # creating the context, here we pass all the columns in the database
                context_vectors_v1 = bandit_helper.get_name_encode_cv_v2(index_arms_for_table, self.columns[table_name], self.column_counts[table_name], constants.CONTEXT_UNIQUENESS, constants.CONTEXT_INCLUDES)
                context_vectors_v2 = bandit_helper.get_derived_value_cv_v4(self.db, index_arms_for_table, query_obj_list_past, chosen_arms_last_round, constants.INDEX_INCLUDES)

                context_vectors = []
                for i in range(len(context_vectors_v1)):
                    context_vectors.append(
                        numpy.array(list(context_vectors_v2[i]) + list(context_vectors_v1[i]), ndmin=2))
                # getting the super arm from the bandit
                chosen_arm_ids[table_name] = self.bandits_dict[table_name].select_arm(context_vectors, t)

                # get objects for the chosen set of arm ids
                if chosen_arm_ids[table_name]:
                    for (arm_id, ucb) in chosen_arm_ids[table_name]:
                        index_name = index_arm_list[arm_id].index_name
                        if table_name not in chosen_arms:
                            chosen_arms[table_name] = {}
                        chosen_arms[table_name][index_name] = (index_arm_list[arm_id], arm_id, ucb)
            
            # setting arms for MV bandit
            if self.with_mv:
                index_arm_list = {}
                index_arms_for_table = {}
                if self.mv in index_arms:
                    index_arm_list = list(index_arms[self.mv].values())
                    index_arms_for_table = index_arms[self.mv]

                logging.info(f"Generated {len(index_arm_list)} arms")
                self.bandits_dict[self.mv].set_arms(index_arm_list)

                context_vectors = bandit_helper.get_view_encode_cv_v1(self.db, index_arms_for_table, self.all_columns,
                                                                      self.number_of_columns, chosen_arms_last_round)
                chosen_arm_ids[self.mv] = self.bandits_dict[self.mv].select_arm(context_vectors, t)
                chosen_arms[self.mv] = {}
                if chosen_arm_ids[self.mv]:
                    for (arm_id, ucb) in chosen_arm_ids[self.mv]:
                        index_name = index_arm_list[arm_id].index_name
                        chosen_arms[self.mv][index_name] = (index_arm_list[arm_id], arm_id, ucb)
        
            super_arm_list, super_context, original_map = bandit_helper.get_super_bandit_context(
                self.db, chosen_arms, chosen_arms_last_round, super_static_context_size, number_of_clusters)
            self.super_bandit.set_arms(super_arm_list)
            super_chosen_arm_ids, mv_size_weight, index_size_weight = self.super_bandit.select_super_arm_v2(super_context)
            super_chosen_per_table = {}
            for c_id in super_chosen_arm_ids:
                c_t, c_aid = original_map[c_id]
                if c_t not in super_chosen_per_table:
                    super_chosen_per_table[c_t] = []
                super_chosen_per_table[c_t].append(c_aid)

            super_chosen_arms = {}
            used_memory = 0
            if super_chosen_arm_ids:
                for arm_id in super_chosen_arm_ids:
                    index_name = super_arm_list[arm_id].index_name
                    super_chosen_arms[index_name] = super_arm_list[arm_id]
                    used_memory = used_memory + super_arm_list[arm_id].memory
                    if index_name in arm_selection_count:
                        arm_selection_count[index_name] += 1
                    else:
                        arm_selection_count[index_name] = 1

            # finding the difference between last round and this round
            keys_last_round = set(chosen_arms_last_round.keys())
            keys_this_round = set(super_chosen_arms.keys())
            key_intersection = keys_last_round & keys_this_round
            key_additions = keys_this_round - key_intersection
            key_deletions = keys_last_round - key_intersection
            logging.info(f"Selected: {keys_this_round}")
            logging.debug(f"Added: {key_additions}")
            logging.debug(f"Removed: {key_deletions}")

            added_arms = {}
            deleted_arms = {}
            for key in key_additions:
                added_arms[key] = super_chosen_arms[key]
            for key in key_deletions:
                deleted_arms[key] = chosen_arms_last_round[key]

            start_time_create_query = datetime.datetime.now()
            bulk_drop(self.db, constants.SCHEMA_NAME, deleted_arms)

            hyp_cost = 0
            useless = set()
            if t < self.hyp_check_rounds:
                # def hyp_check_config(db, schema_name, arm_list_to_add, queries, file_path):
                hyp_query_plans, _ = hyp_check_config(self.db, constants.SCHEMA_NAME,
                                added_arms, query_obj_list_current, self.hyp_file)
                hyp_cost = self.db.get_hyp_cost(self.hyp_file)
                start_time_hyp_reward = datetime.datetime.now()
                hyp_arm_rewards = bandit_helper.calculate_hyp_reward(query_obj_list_current, hyp_query_plans)
                end_time_hyp_reward = datetime.datetime.now()
                hyp_cost += (end_time_hyp_reward - start_time_hyp_reward).total_seconds()
                useless = set(added_arms.keys()) - set(hyp_arm_rewards.keys())
                for a_id in useless:
                    logging.info(f"Suggestion Removed {a_id}")
                    del added_arms[a_id]
                    del super_chosen_arms[a_id]

            result = create_query_v7(self.db, constants.SCHEMA_NAME, added_arms, deleted_arms, query_obj_list_current)
            execution_cost, creation_costs, query_plans, cost_analytical, cost_transactional = result
            arm_rewards = bandit_helper.calculate_reward(creation_costs, query_obj_list_current, query_plans)
            # if constants.LOG_XML:
            #     helper.log_query_xmls(configs.experiment_id, query_obj_list_current, query_plans, t, constants.COMPONENT_MAB)
            end_time_create_query = datetime.datetime.now()
            creation_cost = sum(creation_costs.values())

            self.super_bandit.update_super_v3(super_chosen_arm_ids, arm_rewards, useless, mv_size_weight, index_size_weight)

            for table_name in self.candidate_tables:
                arm_ids = super_chosen_per_table[table_name] if (table_name in super_chosen_per_table) else []
                self.bandits_dict[table_name].update(arm_ids, arm_rewards, useless, mv_size_weight, index_size_weight)

            if self.with_mv:
                arm_ids = super_chosen_per_table[self.mv] if (self.mv in super_chosen_per_table) else []
                self.bandits_dict[self.mv].update(arm_ids, arm_rewards, useless, mv_size_weight, index_size_weight)


            # keeping track of queries that we saw last time
            chosen_arms_last_round = super_chosen_arms

            if t == (self.rounds - 1):
                bulk_drop(self.db, constants.SCHEMA_NAME, super_chosen_arms)

            end_time_round = datetime.datetime.now()
            current_config_size = self.db.get_current_pds_size()
            logging.info("Size taken by the config: " + str(current_config_size) + "MB")
            # Adding information to the results array
            actual_round_number = t
            recommendation_time = (end_time_round - start_time_round).total_seconds() + hyp_cost - (
                        end_time_create_query - start_time_create_query).total_seconds()
            logging.info("Recommendation cost: " + str(recommendation_time) + ", Hyp Component: " + str(hyp_cost))
            total_round_time = creation_cost + execution_cost + recommendation_time
            results.append([actual_round_number, constants.MEASURE_BATCH_TIME, total_round_time])
            results.append([actual_round_number, constants.MEASURE_INDEX_CREATION_COST, creation_cost])
            results.append([actual_round_number, constants.MEASURE_QUERY_EXECUTION_COST, execution_cost])
            results.append(
                [actual_round_number, constants.MEASURE_INDEX_RECOMMENDATION_COST, recommendation_time])
            results.append([actual_round_number, constants.MEASURE_MEMORY_COST, current_config_size])
            results.append([actual_round_number, constants.MEASURE_ANALYTICAL_EXECUTION_COST, cost_analytical])
            results.append([actual_round_number, constants.MEASURE_TRANSACTIONAL_EXECUTION_COST, cost_transactional])

            total_time += total_round_time

            print(f"current total {t}: ", total_time, ", this round: ", total_round_time)
            logging.info(f"current total {t}: {total_time}, this round: {total_round_time}")


    def __str__(self):
        return (
            f"SystemState(\n"
            f"  with_mv={self.with_mv},\n"
            f"  mv='{self.mv}',\n"
            f"  max_memory={self.max_memory},\n"
            f"  db_connected={self.db.conn is not None},\n"
            f"  query_count={len(self.queries)},\n"
            f"  table_count={len(self.tables)},\n"
            f"  candidate_table_count={len(self.candidate_tables)},\n"
            f"  total_columns={self.number_of_columns},\n"
            f"  remaining_memory={self.max_memory},\n"
            f"  cluster_id={self.cluster_id},\n"
            f"  hyp_check_rounds={self.hyp_check_rounds},\n"
            f"  total_rounds={self.rounds}\n"
            f")"
        )
