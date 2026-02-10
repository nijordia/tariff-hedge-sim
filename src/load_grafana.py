"""
Load gold data from DuckDB into Postgres for Grafana visualization.

This script:
1. Reads gold_risk_results (is_latest=true) from DuckDB warehouse
2. Loads it into Postgres dashboard.gold_risk_results table
3. Enables Grafana to query the data efficiently
"""

import os
import sys

import duckdb
import psycopg2
from psycopg2.extras import execute_batch

from src.config_loader import load_config, resolve_path

GOLD_COLUMNS = [
    "invoice_uuid",
    "invoice_id",
    "usd_amount",
    "invoice_date",
    "due_date",
    "horizon_days",
    "hedged_eur",
    "var_95_eur",
    "cvar_95_eur",
    "var_percentage",
    "hedge_ratio",
    "recommendation",
    "prob_loss_positive",
    "expected_loss_eur",
    "prob_loss_gt_10pct",
    "min_loss",
    "max_loss",
    "median_loss",
    "simulation_timestamp",
    "run_date",
]

SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS dashboard;

DROP TABLE IF EXISTS dashboard.gold_risk_results;

CREATE TABLE dashboard.gold_risk_results (
    invoice_uuid VARCHAR(50) PRIMARY KEY,
    invoice_id VARCHAR(50) NOT NULL,
    usd_amount DECIMAL(12, 2),
    invoice_date DATE,
    due_date DATE,
    horizon_days INTEGER,
    hedged_eur DECIMAL(12, 2),
    var_95_eur DECIMAL(12, 2),
    cvar_95_eur DECIMAL(12, 2),
    var_percentage DECIMAL(5, 2),
    hedge_ratio DECIMAL(5, 4),
    recommendation VARCHAR(50),
    prob_loss_positive DECIMAL(5, 4),
    expected_loss_eur DECIMAL(12, 2),
    prob_loss_gt_10pct DECIMAL(5, 4),
    min_loss DECIMAL(12, 2),
    max_loss DECIMAL(12, 2),
    median_loss DECIMAL(12, 2),
    simulation_timestamp TIMESTAMP,
    run_date DATE,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gold_invoice_date ON dashboard.gold_risk_results(invoice_date);
CREATE INDEX IF NOT EXISTS idx_gold_var_pct ON dashboard.gold_risk_results(var_percentage DESC);
CREATE INDEX IF NOT EXISTS idx_gold_hedge_ratio ON dashboard.gold_risk_results(hedge_ratio);
CREATE INDEX IF NOT EXISTS idx_gold_recommendation ON dashboard.gold_risk_results(recommendation);
CREATE INDEX IF NOT EXISTS idx_gold_updated_at ON dashboard.gold_risk_results(updated_at DESC);
"""


def get_postgres_connection():
    """Get Postgres connection using environment variables or defaults."""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'airflow'),
        user=os.getenv('POSTGRES_USER', 'airflow'),
        password=os.getenv('POSTGRES_PASSWORD', 'airflow'),
    )


def load_to_postgres():
    """Copy gold_risk_results (is_latest only) from DuckDB to Postgres."""

    print("Starting Grafana data load...")

    cfg = load_config()
    duckdb_path = resolve_path(cfg, "silver").parent / "warehouse.duckdb"

    if not duckdb_path.exists():
        print(f"ERROR: DuckDB warehouse not found at {duckdb_path}")
        sys.exit(1)

    print(f"Connecting to DuckDB: {duckdb_path}")
    conn_duck = duckdb.connect(str(duckdb_path), read_only=True)

    # Check if gold table exists
    tables = conn_duck.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name = 'gold_risk_results'"
    ).fetchall()

    if not tables:
        print("WARNING: gold_risk_results table not found in DuckDB. Run dbt first.")
        conn_duck.close()
        sys.exit(0)

    # Fetch gold data (latest simulation per invoice only)
    print("Fetching gold data from DuckDB (is_latest=true only)...")
    cols = ", ".join(GOLD_COLUMNS)
    df = conn_duck.execute(f"""
        SELECT {cols}
        FROM gold_risk_results
        WHERE is_latest = true
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

    # Drop and recreate table (handles schema evolution cleanly)
    print("Creating/verifying Postgres schema...")
    cur.execute(SCHEMA_DDL)
    conn_pg.commit()

    # Bulk insert
    print("Inserting new data...")
    placeholders = ", ".join(["%s"] * len(GOLD_COLUMNS))
    insert_query = f"""
        INSERT INTO dashboard.gold_risk_results ({cols})
        VALUES ({placeholders})
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
