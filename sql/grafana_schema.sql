-- ============================================================
-- Grafana Dashboard Schema
-- Creates tables in Postgres for Grafana visualization
-- ============================================================

-- Create schema for dashboard data
CREATE SCHEMA IF NOT EXISTS dashboard;

-- Gold risk metrics table (main dashboard source)
CREATE TABLE IF NOT EXISTS dashboard.gold_risk_results (
    invoice_id VARCHAR(50) PRIMARY KEY,
    invoice_date DATE,
    invoice_value_eur DECIMAL(12, 2),
    contract_value_usd DECIMAL(12, 2),
    hedged_eur DECIMAL(12, 2),
    var_95_eur DECIMAL(12, 2),
    var_percentage DECIMAL(5, 2),
    hedge_ratio DECIMAL(5, 4),
    prob_loss_gt_10pct DECIMAL(5, 4),
    recommendation VARCHAR(50),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for faster dashboard queries
CREATE INDEX IF NOT EXISTS idx_gold_updated_at ON dashboard.gold_risk_results(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_gold_hedge_ratio ON dashboard.gold_risk_results(hedge_ratio);
CREATE INDEX IF NOT EXISTS idx_gold_var_pct ON dashboard.gold_risk_results(var_percentage DESC);
CREATE INDEX IF NOT EXISTS idx_gold_invoice_date ON dashboard.gold_risk_results(invoice_date);

-- Grant permissions (if using separate Grafana user in future)
-- GRANT USAGE ON SCHEMA dashboard TO grafana_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA dashboard TO grafana_user;
