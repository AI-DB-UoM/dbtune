EXTENSION = dbtune_grasp
MODULE_big = dbtune_grasp
OBJS = dbtune_grasp.o
DATA = dbtune_grasp--0.0.1.sql
NO_BC = 1

PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)

SHLIB_LINK += -lcurl
