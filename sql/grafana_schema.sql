-- ============================================================
-- Grafana Dashboard Schema
-- Creates tables in Postgres for Grafana visualization
-- ============================================================

-- Create schema for dashboard data (separate from Airflow metadata)
CREATE SCHEMA IF NOT EXISTS dashboard;

-- Drop and recreate to handle schema evolution cleanly
-- (safe because load_grafana.py does full-refresh anyway)
DROP TABLE IF EXISTS dashboard.gold_risk_results;

-- Gold risk metrics table (main dashboard source)
-- Only is_latest=true rows are loaded, so no is_latest column needed here
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

-- Create indexes for faster dashboard queries
CREATE INDEX IF NOT EXISTS idx_gold_invoice_date ON dashboard.gold_risk_results(invoice_date);
CREATE INDEX IF NOT EXISTS idx_gold_var_pct ON dashboard.gold_risk_results(var_percentage DESC);
CREATE INDEX IF NOT EXISTS idx_gold_hedge_ratio ON dashboard.gold_risk_results(hedge_ratio);
CREATE INDEX IF NOT EXISTS idx_gold_recommendation ON dashboard.gold_risk_results(recommendation);
CREATE INDEX IF NOT EXISTS idx_gold_updated_at ON dashboard.gold_risk_results(updated_at DESC);

-- Grant permissions (if using separate Grafana user in future)
-- GRANT USAGE ON SCHEMA dashboard TO grafana_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA dashboard TO grafana_user;
