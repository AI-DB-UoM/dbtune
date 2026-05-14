CREATE FUNCTION dbtune_mab_tune(tablename TEXT, columns TEXT[])
RETURNS TEXT
AS 'MODULE_PATHNAME', 'dbtune_mab_tune'
LANGUAGE C STRICT;