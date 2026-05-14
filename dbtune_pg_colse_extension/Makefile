EXTENSION = dbtune_colse
MODULE_big = dbtune_colse
OBJS = dbtune_colse.o
DATA = dbtune_colse--0.0.1.sql

PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)

SHLIB_LINK += -lcurl
NO_BC = 1
