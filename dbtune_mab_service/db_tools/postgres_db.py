# postgres_db.py
import psycopg2
from collections import defaultdict
import time
import json
import io
import psycopg2.extras
import datetime

from .column import Column
from .base_db import BaseDB
from .table import Table
from .qplan_pg.query_plan import QueryPlan
import constants

from psycopg2 import sql

class PostgresDB(BaseDB):
    def connect(self):
        self.conn = psycopg2.connect(
            dbname=self.config.get("dbname"),
            user=self.config.get("user"),
            password=self.config.get("password"),
            host=self.config.get("host", "localhost"),
            port=self.config.get("port", 5438),
        )
        self.pk_columns_dict = {}
        self.tables = {}

    def _get_exact_table_row_count(self, table_name):
        query = f"SELECT COUNT(*) FROM public.{table_name};"
        with self.conn.cursor() as cur:
            cur.execute(query)
            return int(cur.fetchone()[0])
        
    def _get_estimated_table_row_count(self, table_name):
        query = """
            SELECT reltuples::BIGINT
            FROM pg_class
            WHERE relname = %s;
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (table_name,))
            return int(cur.fetchone()[0])

    def get_table_row_count(self, table_name, exact=False):
        if exact:
            return self._get_exact_table_row_count(table_name)
        else:
            return self._get_estimated_table_row_count(table_name)

    def get_current_pds_size(self):
        """
        Get total size of all indexes in the current database (in MB)
        """
        query = """
            SELECT SUM(pg_indexes_size(relid)) / (1024 * 1024) AS size_mb
            FROM pg_catalog.pg_statio_user_tables;
        """
        with self.conn.cursor() as cur:
            cur.execute(query)
            result = cur.fetchone()
            return float(result[0])


    def get_columns_for_table(self, table_name):
        columns = {}
        cursor = self.conn.cursor()

        query = """
            SELECT 
                cols.column_name,
                cols.data_type,
                cols.character_maximum_length,
                EXISTS (
                    SELECT 1 
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_name = cols.table_name
                    AND tc.table_schema = cols.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND kcu.column_name = cols.column_name
                    AND cols.table_name = %s
                ) AS is_primary_key
            FROM information_schema.columns cols
            WHERE cols.table_schema = 'public' AND cols.table_name = %s
            ORDER BY cols.ordinal_position
        """
        cursor.execute(query, (table_name, table_name))
        results = cursor.fetchall()

        varchar_cols = []
        for col_name, data_type, max_len, is_pk in results:
            column = Column(table_name, col_name, data_type)
            column.set_max_column_size(max_len if max_len else 0)
            column.set_column_size(max_len if max_len else 0)
            column.set_is_primary_key(is_pk)
            columns[col_name] = column
            if data_type in ['character varying', 'text', 'character']:
                varchar_cols.append(col_name)

        # Step 2: Estimate average length for varchar/text columns
        if varchar_cols:
            inner = ", ".join(f"octet_length({col}) as len_{col}" for col in varchar_cols)
            outer = ", ".join(f"avg(len_{col})" for col in varchar_cols)
            avg_len_query = f"SELECT {outer} FROM (SELECT {inner} FROM {table_name} LIMIT 1000) sub"
            cursor.execute(avg_len_query)
            row = cursor.fetchone()
            for col_name, avg_len in zip(varchar_cols, row):
                columns[col_name].set_column_size(int(avg_len) if avg_len is not None else 0)

        return columns


    def get_all_columns(self):
        """
        Get all columns grouped by table name in the current connected database (public schema).

        :return: 
            - columns: dict[table_name] -> list of column names
            - total_column_count: int
        """
        query = """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public';
        """
        columns = defaultdict(list)
        with self.conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
            for table, column in results:
                columns[table].append(column)
        return dict(columns), len(results)
    
    def get_primary_key(self, table_name):
        """
        Get Primary key of a given table. Note tis might not be in order (not sure)
        :param schema_name: schema name of table
        :param table_name: table name which we want to find the PK
        :return: array of columns
        """
        if table_name in self.pk_columns_dict:
            pk_columns = self.pk_columns_dict[table_name]
        else:
            pk_columns = []
            query = f"""SELECT a.attname, format_type(a.atttypid, a.atttypmod) AS data_type
                        FROM   pg_index i
                        JOIN   pg_attribute a ON a.attrelid = i.indrelid
                                            AND a.attnum = ANY(i.indkey)
                        WHERE  i.indrelid = '{table_name}'::regclass
                        AND    i.indisprimary;"""
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            for result in results:
                pk_columns.append(result[0])
            self.pk_columns_dict[table_name] = pk_columns
        return pk_columns


    def get_tables(self):
        """
        Get all tables as Table objects
        :param connection: SQL Connection
        :return: Table dictionary with table name as the key
        """
        if self.tables:
            return self.tables
        else:
            get_tables_query = """select table_name from information_schema.tables
                                    where table_schema = 'public' and table_type='BASE TABLE'"""
            cursor = self.conn.cursor()
            cursor.execute(get_tables_query)
            results = cursor.fetchall()
            for result in results:
                table_name = result[0]
                row_count = self.get_table_row_count(table_name)
                pk_columns = self.get_primary_key(table_name)
                self.tables[table_name] = Table(table_name, row_count, pk_columns)
                self.tables[table_name].set_columns(self.get_columns_for_table(table_name))
                # print(self.tables[table_name].columns)

        return self.tables


    def create_index(self, tbl_name, col_names, idx_name, include_cols=(), schema_name="public"):
        """
        Create an index on the given table and return the creation time (in seconds).

        :param schema_name: str, schema name (e.g. 'public')
        :param tbl_name: str, table name
        :param col_names: list[str], indexed columns
        :param idx_name: str, index name
        :param include_cols: tuple/list[str], columns to INCLUDE (optional)
        :return: float or None (creation time in seconds, or None on failure)
        """
        if not col_names:
            raise ValueError("col_names cannot be empty")
        if not isinstance(col_names, (list, tuple)) or not all(isinstance(c, str) for c in col_names):
            raise TypeError("col_names must be a list or tuple of strings")
        if include_cols and (not isinstance(include_cols, (list, tuple)) or not all(isinstance(c, str) for c in include_cols)):
            raise TypeError("include_cols must be a list or tuple of strings")
        
        try:
            cursor = self.conn.cursor()
            # Build CREATE INDEX query using psycopg2.sql for safety
            query = sql.SQL("CREATE INDEX {idx} ON {schema}.{table} ({columns}){include};").format(
                idx=sql.Identifier(idx_name),
                schema=sql.Identifier(schema_name),
                table=sql.Identifier(tbl_name),
                columns=sql.SQL(", ").join(map(sql.Identifier, col_names)),
                include=sql.SQL(f" INCLUDE ({', '.join(map(str, include_cols))})") if include_cols else sql.SQL("")
            )

            print("query:", query.as_string(self.conn))
            start = time.time()
            cursor.execute(query)
            self.conn.commit()
            elapsed = time.time() - start
            print(f"[INFO] Index '{idx_name}' created in {elapsed:.3f} seconds.")
            return elapsed
        except Exception as e:
            self.conn.rollback()
            print(f"[ERROR] Failed to create index '{idx_name}': {e}")
            return None
        finally:
            cursor.close()


    def drop_index(self, idx_name, schema_name="public"):
        """
        Drops the index on the given table with given name

        :param connection: sql_connection
        :param idx_name: name of the index
        :return:
        """
        query = f'DROP INDEX IF EXISTS {schema_name}.{idx_name}'
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()
        # logging.info(f"removed: {idx_name}")
        # logging.debug(query)
    

    def create_view(self, view_name, view_query, index_query=None):
        """
        Create a materialized view and (optionally) an index on it.
        Return the index creation time in seconds.
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(f"DROP MATERIALIZED VIEW IF EXISTS {view_name}")
            self.conn.commit()
            start = time.time()
            cursor.execute(view_query)
            self.conn.commit()
            elapsed = time.time() - start
        except Exception as e:
            self.conn.rollback()
            print(f"View creation failed: {e}")
            return 0

        if index_query:
            try:
                start = time.time()
                cursor.execute(index_query)
                self.conn.commit()
                elapsed = time.time() - start
                print(f"Index creation on view took {elapsed:.3f} seconds")
                return elapsed
            except Exception as e:
                self.conn.rollback()
                print(f"Index creation failed: {e}")
                return 0
            finally:
                cursor.close()
        else:
            cursor.close()
            return 0


    def drop_view(self, view_name, materialized=True):
        """
        Drops the (materialized) view with the given name if it exists.

        :param view_name: The name of the view to drop.
        :param materialized: Whether the view is materialized.
        """
        drop_type = "MATERIALIZED VIEW" if materialized else "VIEW"
        query = f"DROP {drop_type} IF EXISTS {view_name}"
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"[ERROR] Failed to drop {drop_type} '{view_name}': {e}")
        finally:
            cursor.close()


    def get_arm_size(self, index_name):
        """
        Estimate index size in MB in PostgreSQL and assign it to bandit_arm.memory.
        """
        # index_name = bandit_arm.index_name  # should include schema if needed
        query = f"""
            SELECT pg_relation_size('{index_name}') / 1024.0 / 1024.0 AS size_mb;
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        return float(result[0]) if result and result[0] is not None else 0.0


    def get_arm_size_mv(self, view_name):
        """
        Get the size (in MB) of a materialized view in PostgreSQL
        and assign it to bandit_arm.memory.
        """
        # view_name = bandit_arm.index_name  # should be schema-qualified or use separate schema arg
        query = f"""
            SELECT pg_total_relation_size('{view_name}') / 1024.0 / 1024.0 AS size_mb;
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        return float(result[0]) if result and result[0] is not None else 0.0


    def get_database_size(self):
        """
        Return database size in MB (float).
        """
        database = self.config.get("dbname")
        try:
            query = f"SELECT pg_database_size('{database}');"
            cursor = self.conn.cursor()
            cursor.execute(query)
            size_bytes = cursor.fetchone()[0]
            return round(size_bytes / (1024 * 1024), 2)  # MB
        except Exception as e:
            print("Exception when get_database_size:", e)
            return -1.0


    def execute_query_v2(self, query, print_exc=True):
        """
        Execute the given SQL query with EXPLAIN ANALYZE (JSON format), and return parsed IndexUse objects.

        :param query: SQL string to execute
        :param print_exc: If True, print exceptions
        :return: List of IndexUse instances parsed from the plan
        """
        try:
            cursor = self.conn.cursor()
            # Run query with EXPLAIN ANALYZE
            cursor.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {query}")
            plan_json = cursor.fetchone()[0]
            return QueryPlan.get_plan(json.dumps(plan_json), query)
        except Exception as e:
            if print_exc:
                print("[ERROR]", e)
            return None


    # TODO Is drop view important here?
    def hyp_create_view(self, view_name, view_query, index_def, file):
        """
        Create a materialized view and a hypothetical index on it using hypopg (PostgreSQL).
        Return the hypothetical index creation time in seconds.
        
        :param view_name: name of the materialized view
        :param view_query: SQL to create the view
        :param index_def: index definition, e.g., "CREATE INDEX ON schema.view(col1, col2)"
        :param file: writable file handle to log index statement
        """
        cursor = self.conn.cursor()

        # Drop if exists
        cursor.execute(f"DROP MATERIALIZED VIEW IF EXISTS {view_name}")
        self.conn.commit()

        try:
            # Create materialized view
            start_time = datetime.datetime.now()
            cursor.execute(view_query)
            self.conn.commit()
            view_creation_time = (datetime.datetime.now() - start_time).total_seconds()
        except Exception as e:
            self.conn.rollback()
            print(f"View creation failed: {e}")
            return 0

        try:
            # Ensure hypopg is available
            cursor.execute("CREATE EXTENSION IF NOT EXISTS hypopg;")

            # Create hypothetical index
            start_time = datetime.datetime.now()
            cursor.execute(f"SELECT * FROM hypopg_create_index('{[index_def[:-1]]}');")
            end_time = datetime.datetime.now()

            file.write(index_def + '\n')
            self.conn.commit()

            return (end_time - start_time).total_seconds()
        except Exception as e:
            self.conn.rollback()
            print(f"Hypothetical index creation failed: {e}")
            return 0
        finally:
            # Always clear hypothetical indexes
            # try:
            #     cursor.execute("SELECT hypopg_reset();")
            #     self.conn.commit()
            # except Exception as e:
            #     self.conn.rollback()
            #     print(f"Hypopg reset failed: {e}")
            cursor.close()


    def hyp_create_index_v1(self, schema_name, tbl_name, col_names, idx_name, file, include_cols=()):
        """
        Create a hypothetical index on the given table using hypopg in PostgreSQL.

        :param schema_name: name of the database schema
        :param tbl_name: name of the table
        :param col_names: list of column names for the index
        :param idx_name: name of the index (only for logging)
        :param file: file handle to write the index definition
        :param include_cols: optional columns to include
        :return: time taken to simulate index creation
        """
        cursor = self.conn.cursor()

        # Ensure hypopg is enabled
        cursor.execute("CREATE EXTENSION IF NOT EXISTS hypopg;")

        # Build the index definition
        index_def = f"CREATE INDEX ON {schema_name}.{tbl_name} ({', '.join(col_names)})"
        if include_cols:
            index_def += f" INCLUDE ({', '.join(include_cols)})"

        query = f"SELECT * FROM hypopg_create_index('{index_def}');"

        try:
            start_time = datetime.datetime.now()
            cursor.execute(query)
            end_time = datetime.datetime.now()

            if file:
                file.write(index_def + '\n')
            self.conn.commit()

            return (end_time - start_time).total_seconds()
        except Exception as e:
            self.conn.rollback()
            print(f"Hypothetical index creation failed: {e}")
            return 0
        finally:
            # Clear all hypothetical indexes
            # try:
            #     cursor.execute("SELECT hypopg_reset();")
            #     self.conn.commit()
            # except Exception as e:
            #     self.conn.rollback()
            #     print(f"Failed to reset hypopg: {e}")
            cursor.close()


    def hyp_enable_index(self, file=None):
        """
        List all hypothetical indexes from hypopg and write to file or in-memory buffer if file is None or empty.
        """
        if file is None:
            file = io.StringIO()

        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    idx.indexrelid::regclass::text AS indexname,
                    hypopg_get_indexdef(idx.indexrelid) AS indexdef
                FROM hypopg() AS idx;
            """)
            result_rows = cursor.fetchall()

            for relname, indexdef in result_rows:
                # file.write(f"-- Hypothetical index on {relname}\n")
                file.write(indexdef + ";\n")
        except Exception as e:
            self.conn.rollback()
            print(f"Failed to list hypothetical indexes: {e}")
        finally:
            cursor.close()

        return file  # return file in case caller wants to read its contents


    def hyp_execute_query_v2(self, query, file, print_exc=True):
        """
        Executes the given query using EXPLAIN ANALYZE (FORMAT JSON) in PostgreSQL,
        and returns the parsed QueryPlan object — intended for use with hypothetical indexes.

        :param query: SQL query to execute
        :param print_exc: Whether to print exceptions
        :return: Parsed QueryPlan instance, or None on failure
        """
        try:
            cursor = self.conn.cursor()
            explain_query = f"EXPLAIN (ANALYZE, FORMAT JSON) {query}"
            start_time = datetime.datetime.now()
            cursor.execute(explain_query)
            end_time = datetime.datetime.now()
            # file.write(query + '\n')
            execution_time = (end_time - start_time).total_seconds()
            plan_json = cursor.fetchone()[0]  # returns a 1-element array
            return QueryPlan.get_plan(json.dumps(plan_json), query), execution_time  # match original behavior
        except Exception as e:
            if print_exc:
                print(f"[ERROR] Hyp query failed: {e}")
            return None, 0
        
    
    def get_hyp_cost(self, file_path):
        """
        Execute SQL queries from a file and return the total execution time in seconds.
        Intended for use with hypothetical indexes (e.g., created via hypopg).

        :param file_path: str, path to the SQL file
        :return: float, total execution time in seconds
        """
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                query_lines = [
                    line[:-1] for line in lines
                    if line.strip() and not line.strip().startswith('--')
                ]
                # query = ' '.join(query_lines).strip()
                if not query_lines:
                    print("[WARN] Query file is empty or only contains comments.")
                    return 0.0

            cursor = self.conn.cursor()
            start_time = datetime.datetime.now()
            for query_line in query_lines:
                hyp_query = f"SELECT * FROM hypopg_create_index('{query_line}')"
                print("-----------------------")
                print("hyp_query:", hyp_query)
                print("-----------------------")
                cursor.execute(hyp_query)
            end_time = datetime.datetime.now()

            self.conn.commit()
            elapsed = (end_time - start_time).total_seconds()
            print(f"[INFO] Query executed in {elapsed:.4f} seconds.")
            return elapsed

        except Exception as e:
            print("[ERROR] Failed during get_hyp_cost:", e)
            try:
                self.conn.rollback()
            except Exception:
                pass
            return 0.0
        finally:
            if cursor:
                cursor.close()
