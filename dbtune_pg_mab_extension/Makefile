EXTENSION = dbtune_mab
MODULE_big = dbtune_mab
OBJS = dbtune_mab.o
DATA = dbtune_mab--0.0.1.sql
NO_BC = 1

PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)

SHLIB_LINK += -lcurl
