EXTENSION = dbtune_mab
MODULE_big = dbtune_mab
OBJS = dbtune_mab.o

PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)

SHLIB_LINK += -lcurl
NO_BC = 1
