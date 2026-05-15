CREATE FUNCTION dbtune_grasp_estimate(sql_text TEXT)
RETURNS TEXT
AS 'MODULE_PATHNAME', 'dbtune_grasp_estimate'
LANGUAGE C STRICT;
