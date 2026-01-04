
TABLE_SCAN_TIME_LENGTH = 10000


LOG_PATH = "./logs"

# ===============================  Database / Workload  ===============================
SCHEMA_NAME = 'public'
SERVER_RESTART = True
RESTORE_BACKUP = False

# ===============================  Arm Generation Heuristics  ===============================
INDEX_INCLUDES = 1
SMALL_TABLE_IGNORE = 10000

# ===============================  Context Related  ===============================
CONTEXT_UNIQUENESS = 0
CONTEXT_INCLUDES = False
STATIC_CONTEXT_SIZE = 3

# ===============================  Bandit Parameters  ===============================
ALPHA_REDUCTION_RATE = 1.05
QUERY_MEMORY = 1
MAX_INDEXES_PER_TABLE = 10
CREATION_COST_REDUCTION_FACTOR = 4
UNIFORM_ASSUMPTION_START = 10

# ===============================  Reward Related  ===============================
COST_TYPE_ELAPSED_TIME = 'act_elapsed_max'
COST_TYPE_CPU_TIME = 'act_cpu_sum'
COST_TYPE_SUB_TREE_COST = 'sub_tree_cost'
COST_TYPE_CURRENT_EXECUTION = COST_TYPE_ELAPSED_TIME
UNCLAIMED_REWARD_DISTRIBUTION = True

# ===============================  Context Related  ===============================
CONTEXT_UNIQUENESS = 0
CONTEXT_INCLUDES = False
STATIC_CONTEXT_SIZE = 3

# ===============================  PDS Selection  ===============================
VIEW_ONLY = 'VIEW_ONLY'
INDICES_ONLY = 'INDICES_ONLY'
VIEW_AND_INDICES = 'VIEW_AND_INDICES'

# ===============================  Reporting Related  ===============================
DF_COL_COMP_ID = "Component"
DF_COL_REP = "Rep"
DF_COL_BATCH = "Batch Number"
DF_COL_BATCH_COUNT = "# of Batches"
DF_COL_MEASURE_NAME = "Measurement Name"
DF_COL_MEASURE_VALUE = "Measurement Value"

MEASURE_TOTAL_WORKLOAD_TIME = "Total Workload Time"
MEASURE_INDEX_CREATION_COST = "Index Creation Time"
MEASURE_INDEX_RECOMMENDATION_COST = "Index Recommendation Cost"
MEASURE_QUERY_EXECUTION_COST = "Query Execution Cost"
MEASURE_ANALYTICAL_EXECUTION_COST = "Analytical Execution Cost"
MEASURE_TRANSACTIONAL_EXECUTION_COST = "Transactional Execution Cost"
MEASURE_MEMORY_COST = "Memory Cost"
MEASURE_BATCH_TIME = "Batch Time"
MEASURE_HYP_BATCH_TIME = "Hyp Batch Time"

COMPONENT_WARM_UP = "WARM_UP"
COMPONENT_MAB = "MAB"
COMPONENT_TA = 'TA'
COMPONENT_TA_OPTIMAL = "TA_OPTIMAL"
COMPONENT_TA_FULL = "TA_FULL"
COMPONENT_TA_CURRENT = "TA_CURRENT"
COMPONENT_TA_SCHEDULE = "TA_SCHEDULE"
COMPONENT_OPTIMAL = "OPTIMAL"
COMPONENT_NO_INDEX = "NO_INDEX"

TA_WORKLOAD_TYPE_OPTIMAL = 'optimal'
TA_WORKLOAD_TYPE_FULL = 'full'
TA_WORKLOAD_TYPE_CURRENT = 'current'
TA_WORKLOAD_TYPE_SCHEDULE = 'schedule'

QUERY_MEMORY = 1

max_memory = 25000
input_alpha = 1
input_lambda = 0.5