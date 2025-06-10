import constants
import copy

class Query:
    def __init__(self, query_id, query_string, predicates, payloads, time_stamp=0):
        query_string = query_string.lower()
        self.id = query_id
        self.predicates = predicates
        self.payload = payloads
        self.group_by = {}
        self.query_strings = [query_string]
        self.query_string = query_string
        self.frequency = 1
        self.last_seen = time_stamp
        self.first_seen = time_stamp
        self.table_scan_times = {}
        self.index_scan_times = {}
        self.table_scan_times_hyp = {}
        self.index_scan_times_hyp = {}
        self.context = None
        self.next_execution = 0
        self.original_running_time = 0
        self.original_hyp_running_time = 0
        if query_string.strip().startswith('select') or query_string.strip().startswith('with'):
            self.is_analytical = True
        else:
            self.is_analytical = False
            if type(self.id) != str:
                raise Exception('Assumption failed')

    def init_scan_time(self, db_tables):
        for table in db_tables:
            self.table_scan_times[table] = []
            self.index_scan_times[table] = []
            self.table_scan_times_hyp[table] = []
            self.index_scan_times_hyp[table] = []

    def __hash__(self):
        return self.id

    def get_query_string(self, hyp=False):
        query_string = self.query_strings[self.next_execution]
        if not hyp:
            self.next_execution += 1
        return query_string

    def __str__(self):
        return (
            f"Query(\n"
            f"  id={self.id},\n"
            f"  frequency={self.frequency},\n"
            f"  first_seen={self.first_seen},\n"
            f"  last_seen={self.last_seen},\n"
            f"  is_analytical={self.is_analytical},\n"
            f"  query_strings={self.query_strings},\n"
            f"  predicates={self.predicates},\n"
            f"  group_by={self.group_by},\n"
            f"  payload={self.payload},\n"
            f"  original_running_time={self.original_running_time},\n"
            f"  original_hyp_running_time={self.original_hyp_running_time},\n"
            f"  next_execution={self.next_execution}\n"
            f")"
        )
