"""
Load gold data from DuckDB into Postgres for Grafana visualization.

This script:
1. Reads gold_risk_results from DuckDB warehouse
2. Loads it into Postgres dashboard.gold_risk_results table
3. Enables Grafana to query the data efficiently
"""

import os
import sys
from pathlib import Path
import yaml
import duckdb
import psycopg2
from psycopg2.extras import execute_batch


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_postgres_connection():
    """Get Postgres connection using environment variables or defaults."""
    # Try environment variables first (from .env)
    host = os.getenv('POSTGRES_HOST', 'postgres')  # Docker service name
    port = os.getenv('POSTGRES_PORT', '5432')
    database = os.getenv('POSTGRES_DB', 'airflow')
    user = os.getenv('POSTGRES_USER', 'airflow')
    password = os.getenv('POSTGRES_PASSWORD', 'airflow')

    return psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )


def load_to_postgres():
    """Copy gold_risk_results from DuckDB to Postgres."""

    print("Starting Grafana data load...")

    # Load config
    config = load_config()

    # Connect to DuckDB
    duckdb_path = Path(config['paths']['warehouse'])
    if not duckdb_path.exists():
        print(f"ERROR: DuckDB warehouse not found at {duckdb_path}")
        sys.exit(1)

    print(f"Connecting to DuckDB: {duckdb_path}")
    conn_duck = duckdb.connect(str(duckdb_path), read_only=True)

    # Check if gold table exists
    tables = conn_duck.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name = 'gold_risk_results'"
    ).fetchall()

    if not tables:
        print("WARNING: gold_risk_results table not found in DuckDB. Run dbt first.")
        conn_duck.close()
        sys.exit(0)  # Exit gracefully

    # Fetch gold data
    print("Fetching gold data from DuckDB...")
    df = conn_duck.execute("""
        SELECT
            invoice_id,
            invoice_date,
            invoice_value_eur,
            contract_value_usd,
            hedged_eur,
            var_95_eur,
            var_percentage,
            hedge_ratio,
            prob_loss_gt_10pct,
            recommendation
        FROM gold_risk_results
    """).fetchdf()

    conn_duck.close()

    if df.empty:
        print("WARNING: No data in gold_risk_results. Nothing to load.")
        sys.exit(0)

    print(f"Fetched {len(df)} invoices from DuckDB")

    # Connect to Postgres
    print("Connecting to Postgres...")
    conn_pg = get_postgres_connection()
    cur = conn_pg.cursor()

    # Create schema and table if not exists
    print("Creating/verifying Postgres schema...")
    schema_path = Path(__file__).parent.parent / 'sql' / 'grafana_schema.sql'
    with open(schema_path) as f:
        cur.execute(f.read())
    conn_pg.commit()

    # Truncate and reload (simple full-refresh approach)
    print("Clearing existing data...")
    cur.execute("TRUNCATE TABLE dashboard.gold_risk_results")

    # Bulk insert using execute_batch for performance
    print("Inserting new data...")
    insert_query = """
        INSERT INTO dashboard.gold_risk_results (
            invoice_id, invoice_date, invoice_value_eur, contract_value_usd,
            hedged_eur, var_95_eur, var_percentage, hedge_ratio,
            prob_loss_gt_10pct, recommendation
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    data = [tuple(row) for row in df.values]
    execute_batch(cur, insert_query, data, page_size=100)

    conn_pg.commit()

    # Verify load
    cur.execute("SELECT COUNT(*) FROM dashboard.gold_risk_results")
    count = cur.fetchone()[0]

    cur.close()
    conn_pg.close()

    print(f"SUCCESS: Loaded {count} invoices into Postgres for Grafana")
    print("Dashboard data is ready at: dashboard.gold_risk_results")


if __name__ == '__main__':
    try:
        load_to_postgres()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
