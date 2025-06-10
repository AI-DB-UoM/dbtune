import os
import sys
import pytest
import io
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_tools.column import Column

from db_tools.postgres_db import PostgresDB

def _get_db_config():
    return {
        "dbname": "pgdb",
        "user": "pguser",
        "password": "123456",
        "host": "localhost",
        "port": 5438
    }

@pytest.fixture(scope="session")
def db():
    config = _get_db_config()
    db = PostgresDB(config)
    db.connect()
    yield db
    if db.conn and db.conn.closed == 0:
        db.conn.close()


def ensure_connection(db):
    if db.conn is None or db.conn.closed != 0:
        try:
            db.connect()
        except Exception as e:
            print(f"[ERROR] Reconnecting failed: {e}")
            raise

@pytest.mark.order(1)
def test_db_connects_successfully(db):
    assert db.conn is not None

@pytest.mark.order(2)
def test_get_table_row_count(db):
    table_name = "customer"
    count = db.get_table_row_count(table_name)
    # print("test_get_table_row_count:", table_name)
    # print("test_get_table_row_count:", count)
    assert isinstance(count, int) and count >= 0

@pytest.mark.order(3)
def test_get_current_pds_size(db):
    size = db.get_current_pds_size()
    # print("test_get_current_pds_size:", size)
    assert isinstance(size, float) or size is None

# @pytest.mark.order(4)
# def test_get_columns_for_table(db):
#     tables = db.get_tables()
#     assert tables, "No tables found in the database."

#     table_name = next(iter(tables))
#     # print(f"Testing table: {table_name}")

#     cols = db.get_columns_for_table(table_name)
#     # print(f"Columns: {cols}")

#     assert isinstance(cols, list), "Columns should be a list."
#     assert all(isinstance(c, str) for c in cols), "All column names should be strings."
#     assert len(cols) > 0, "Table should have at least one column."

@pytest.mark.order(4)
def test_get_columns_for_table(db):

    tables = db.get_tables()
    assert tables, "No tables found in the database."

    table_name = next(iter(tables))
    # table_name = "customer"
    columns = db.get_columns_for_table(table_name)

    assert isinstance(columns, dict)
    # assert "c_customer_id" in columns or "customer_id" in columns

    for k, v in columns.items():
        print(f"{k}: {v}")

    for col in columns.values():
        assert isinstance(col, Column)
        assert col.table_name == table_name
        assert isinstance(col.column_name, str)
        assert isinstance(col.column_type, str)
        assert isinstance(col.column_size, int)
        assert isinstance(col.max_column_size, int)


@pytest.mark.order(5)
def test_get_all_columns(db):
    all_cols, total = db.get_all_columns()
    # print(all_cols, total)
    assert isinstance(all_cols, dict)
    assert isinstance(total, int)
    print(f"all_cols, total: {all_cols}, {total}")
    assert total > 0

@pytest.mark.order(6)
def test_get_primary_key(db):
    tables = db.get_tables()
    assert len(tables) > 0, "No tables found in the database"

    for table_name in tables:
        pk = db.get_primary_key(table_name)
        # print(f"[{table_name}] Primary Key: {pk}")
        assert isinstance(pk, list)

@pytest.mark.order(7)
def test_get_tables(db):
    tables = db.get_tables()
    # print("\n[TABLES]", tables)
    # print("[TABLE NAMES]", list(tables.keys()))
    assert isinstance(tables, dict)
    assert len(tables) > 0

# Constants for testing
SCHEMA_NAME = "public"
TABLE_NAME = "store_sales"
INDEX_NAME = "test_idx"
VIEW_NAME = "test_mv"
COLUMN_NAMES = ["ss_item_sk", "ss_ticket_number"]

@pytest.fixture(scope="module")
def clean_index(db):
    # Ensure index doesn't exist before/after
    db.drop_index(INDEX_NAME)
    yield
    db.drop_index(INDEX_NAME)

@pytest.fixture(scope="module")
def clean_view(db):
    # Ensure view doesn't exist before/after
    db.drop_view(VIEW_NAME, materialized=True)
    yield
    db.drop_view(VIEW_NAME, materialized=True)

@pytest.mark.order(8)
def test_create_index(db, clean_index):

    elapsed = db.create_index(TABLE_NAME, COLUMN_NAMES, INDEX_NAME, include_cols=(), schema_name=SCHEMA_NAME)
    assert elapsed is not None and elapsed > 0

    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT indexname FROM pg_indexes 
        WHERE schemaname = %s AND tablename = %s AND indexname = %s
    """, (SCHEMA_NAME, TABLE_NAME, INDEX_NAME))
    result = cursor.fetchone()
    print("result:", result)
    assert result is not None and result[0] == INDEX_NAME
    cursor.close()

@pytest.mark.order(9)
def test_drop_index(db):

    db.drop_index(INDEX_NAME)

    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT indexname FROM pg_indexes 
        WHERE schemaname = %s AND tablename = %s AND indexname = %s
    """, (SCHEMA_NAME, TABLE_NAME, INDEX_NAME))
    result = cursor.fetchone()
    assert result is None
    cursor.close()

@pytest.mark.order(10)
def test_create_view(db, clean_view):
    view_query = f"CREATE MATERIALIZED VIEW {VIEW_NAME} AS SELECT * FROM {SCHEMA_NAME}.{TABLE_NAME} LIMIT 10"
    index_query = f"CREATE INDEX {VIEW_NAME}_idx ON {VIEW_NAME} ({', '.join(COLUMN_NAMES)})"
    elapsed = db.create_view(VIEW_NAME, view_query, index_query)
    assert elapsed >= 0

    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT matviewname FROM pg_matviews
        WHERE schemaname = %s AND matviewname = %s
    """, (SCHEMA_NAME, VIEW_NAME))
    result = cursor.fetchone()
    assert result is not None and result[0] == VIEW_NAME
    cursor.close()

@pytest.mark.order(11)
def test_drop_view(db):
    view_query = f"CREATE MATERIALIZED VIEW {VIEW_NAME} AS SELECT * FROM {SCHEMA_NAME}.{TABLE_NAME} LIMIT 10"
    db.create_view(VIEW_NAME, view_query)
    db.drop_view(VIEW_NAME, materialized=True)

    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT matviewname FROM pg_matviews
        WHERE schemaname = %s AND matviewname = %s
    """, (SCHEMA_NAME, VIEW_NAME))
    result = cursor.fetchone()
    assert result is None
    cursor.close()

@pytest.mark.order(12)
def test_get_arm_size(db, clean_index):
    # db.create_index(SCHEMA_NAME, TABLE_NAME, COLUMN_NAMES, INDEX_NAME)
    elapsed = db.create_index(TABLE_NAME, COLUMN_NAMES, INDEX_NAME, include_cols=(), schema_name=SCHEMA_NAME)

    full_index_name = f"{SCHEMA_NAME}.{INDEX_NAME}"
    size = db.get_arm_size(full_index_name)
    assert size > 0

@pytest.mark.order(13)
def test_get_arm_size_mv(db, clean_view):
    view_query = f"CREATE MATERIALIZED VIEW {VIEW_NAME} AS SELECT * FROM {SCHEMA_NAME}.{TABLE_NAME} LIMIT 10"
    db.create_view(VIEW_NAME, view_query)

    full_view_name = f"{SCHEMA_NAME}.{VIEW_NAME}"
    size = db.get_arm_size_mv(full_view_name)
    assert size > 0

import pytest
from db_tools.postgres_db import PostgresDB
from db_tools.qplan_pg.query_plan import QueryPlan
from db_tools.qplan_pg.index_use import PgIndexRead, PgIndexWrite

TEST_QUERY = "SELECT ss_item_sk FROM store_sales WHERE ss_item_sk = 100"

@pytest.mark.order(14)
def test_execute_query_v2(db):
    index_uses = db.execute_query_v2(TEST_QUERY)

    # Check the return type
    assert isinstance(index_uses, list)
    assert all(isinstance(x, (PgIndexRead, PgIndexWrite)) for x in index_uses)

    # Optional: inspect content of first entry
    if index_uses:
        iu = index_uses[0]
        print("Index:", iu.indices[0].index)
        print("Table:", iu.indices[0].table)
        print("Elapsed Time:", iu.act_elapsed_max)
        print("Rows Output:", iu.act_rows_output)

@pytest.mark.order(15)
def test_hyp_create_index_v1(db):
    file = io.StringIO()

    elapsed = db.hyp_create_index_v1(
        schema_name=SCHEMA_NAME,
        tbl_name=TABLE_NAME,
        col_names=COLUMN_NAMES,
        idx_name='hyp_idx_test',
        file=file,
        include_cols=[]
    )

    assert elapsed is not None and elapsed > 0
    assert "CREATE INDEX ON" in file.getvalue()

    print(file.getvalue())
    print(f"elapsed: {elapsed}")

    ensure_connection(db)
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT indexname FROM pg_indexes 
        WHERE schemaname = %s AND tablename = %s AND indexname = %s
    """, (SCHEMA_NAME, TABLE_NAME, 'hyp_idx_test'))
    result = cursor.fetchone()
    assert result is None  
    cursor.close()


INDEX_DEF = f"CREATE INDEX ON {SCHEMA_NAME}.{VIEW_NAME}({', '.join(COLUMN_NAMES)})"

@pytest.mark.order(16)
def test_hyp_create_view(db):

    ensure_connection(db)

    view_query = f"""
        CREATE MATERIALIZED VIEW {SCHEMA_NAME}.{VIEW_NAME} AS
        SELECT {', '.join(COLUMN_NAMES)}, COUNT(*) AS cnt
        FROM {SCHEMA_NAME}.{TABLE_NAME}
        GROUP BY {', '.join(COLUMN_NAMES)}
    """

    file = io.StringIO()

    elapsed = db.hyp_create_view(
        view_name=VIEW_NAME,
        view_query=view_query,
        index_def=INDEX_DEF,
        file=file
    )

    print(file.getvalue())
    print(f"elapsed: {elapsed}")

    assert elapsed > 0
    assert "CREATE INDEX ON" in file.getvalue()


@pytest.mark.order(17)
def test_hyp_execute_query_v2(db):

    ensure_connection(db)

    view_query = f"""
        CREATE MATERIALIZED VIEW {SCHEMA_NAME}.{VIEW_NAME} AS
        SELECT {', '.join(COLUMN_NAMES)}, COUNT(*) AS cnt
        FROM {SCHEMA_NAME}.{TABLE_NAME}
        GROUP BY {', '.join(COLUMN_NAMES)}
    """

    index_def = f"CREATE INDEX ON {SCHEMA_NAME}.{VIEW_NAME}(ss_item_sk)"

    ensure_connection(db)
    cursor = db.conn.cursor()
    cursor.execute(f"DROP MATERIALIZED VIEW IF EXISTS {SCHEMA_NAME}.{VIEW_NAME}")
    db.conn.commit()

    cursor.execute(view_query)
    db.conn.commit()

    cursor.execute("CREATE EXTENSION IF NOT EXISTS hypopg;")
    cursor.execute(f"SELECT * FROM hypopg_create_index('{index_def}')")
    db.conn.commit()

    file = io.StringIO()
    index_uses, _ = db.hyp_execute_query_v2(TEST_QUERY, file)

    # Check the return type
    assert isinstance(index_uses, list)
    assert all(isinstance(x, (PgIndexRead, PgIndexWrite)) for x in index_uses)

    # Optional: inspect content of first entry
    if index_uses:
        iu = index_uses[0]
        print("Index:", iu.indices[0].index)
        print("Table:", iu.indices[0].table)
        print("Elapsed Time:", iu.act_elapsed_max)
        print("Rows Output:", iu.act_rows_output)


@pytest.mark.order(18)
def test_hyp_enable_index(db):

    ensure_connection(db)

    cursor = db.conn.cursor()
    try:
        cursor.execute("SELECT hypopg_reset();")
        db.conn.commit()
    except Exception as e:
        db.conn.rollback()
        print(f"Hypopg reset failed: {e}")

    view_query = f"""
        CREATE MATERIALIZED VIEW {SCHEMA_NAME}.{VIEW_NAME} AS
        SELECT {', '.join(COLUMN_NAMES)}, COUNT(*) AS cnt
        FROM {SCHEMA_NAME}.{TABLE_NAME}
        GROUP BY {', '.join(COLUMN_NAMES)}
    """

    file = io.StringIO()

    # Step 1: Create view + hypothetical index
    elapsed = db.hyp_create_view(
        view_name=VIEW_NAME,
        view_query=view_query,
        index_def=INDEX_DEF,
        file=file
    )

    ensure_connection(db)

    print(file.getvalue())
    print(f"elapsed: {elapsed}")

    # Step 2: Enable hypothetical indexes and collect log
    file_buffer = db.hyp_enable_index()
    print(f"file_buffer.getvalue(): [{file_buffer.getvalue()}]")

    output = file_buffer.getvalue()
    assert f"CREATE INDEX ON {SCHEMA_NAME}.{VIEW_NAME}" in output
    assert "-- Hypothetical index on" in output

# pytest tests/test_postgred_db.py -s

# pytest tests/test_postgred_db.py -k test_db_connects_successfully -s
# pytest tests/test_postgred_db.py -k test_get_table_row_count -s
# pytest tests/test_postgred_db.py -k test_get_current_pds_size -s
# pytest tests/test_postgred_db.py -k test_get_columns_for_table -s
# pytest tests/test_postgred_db.py -k test_get_all_columns -s
# pytest tests/test_postgred_db.py -k test_get_primary_key -s
# pytest tests/test_postgred_db.py -k test_get_tables -s
# pytest tests/test_postgred_db.py -k test_create_index -s
# pytest tests/test_postgred_db.py -k test_drop_index -s
# pytest tests/test_postgred_db.py -k test_create_view -s
# pytest tests/test_postgred_db.py -k test_drop_view -s

# pytest tests/test_postgred_db.py -k test_get_arm_size_mv -s
# pytest tests/test_postgred_db.py -k test_execute_query_v2 -s
# pytest tests/test_postgred_db.py -k test_hyp_create_index_v1 -s
# pytest tests/test_postgred_db.py -k test_hyp_create_view -s
# pytest tests/test_postgred_db.py -k test_hyp_enable_index -s
# pytest tests/test_postgred_db.py -k test_hyp_execute_query_v2 -s
