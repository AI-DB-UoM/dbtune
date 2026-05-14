CREATE FUNCTION dbtune_colse_estimate(sql_text TEXT)
RETURNS TEXT
AS 'MODULE_PATHNAME', 'dbtune_colse_estimate'
LANGUAGE C STRICT;
