# Tariff Hedge Simulator

A realistic FX + tariff risk simulation pipeline demonstrating modern data engineering practices. Built as a portfolio project targeting Kantox-style FX risk management workflows.

## Business Story

A small Barcelona olive oil exporter sells to the US in USD with 90–200 day payment terms. They face two risks:

1. **EUR/USD volatility** — revenue loss when converting USD back to EUR
2. **Tariff shocks** — hypothetical US tariffs reducing effective USD revenue

The pipeline quantifies the downside risk of *not hedging* using Monte Carlo simulation, VaR/CVaR metrics, and produces a hedge recommendation ("hedge now or wait?").

## Architecture

```
┌──────────────┐     ┌─────────┐     ┌─────────────┐     ┌──────────────┐
│   Generator  │────▶│  Bronze  │────▶│  Silver      │────▶│  Simulation  │
│  (invoices)  │     │  (CSV)   │     │  (dbt/DuckDB)│     │  (Monte Carlo│
└──────────────┘     └─────────┘     └─────────────┘     └──────┬───────┘
                                                                │
                     ┌─────────┐     ┌─────────────┐           │
                     │  Alerts  │◀───│    Gold      │◀──────────┘
                     │  (JSON)  │    │  (dbt/DuckDB)│
                     └─────────┘     └─────────────┘

Orchestration: Apache Airflow  │  Storage: Local (Parquet/CSV)
Dashboard: Grafana             │  Database: DuckDB
```

**Medallion Architecture:**
- **Bronze** — raw CSV, append-only, partitioned by `run_date`
- **Silver** — cleaned + validated via dbt, with traceability columns
- **Gold** — enriched risk results, historical tracking with `is_latest` flag
- **Alerts** — per-invoice JSON files for downstream consumption

## Tech Stack

| Component | Tool |
|-----------|------|
| Language | Python 3.11 |
| Transformations | dbt Core + dbt-duckdb |
| Database | DuckDB (embedded) |
| Orchestration | Apache Airflow 2.8 |
| Containers | Docker + docker-compose |
| Dashboard | Grafana 10 |
| Storage | Local filesystem (Parquet, CSV, JSON) |

All free and open-source. No cloud services required.

## Risk Logic

1. **GBM Simulation**: 10,000 Monte Carlo paths for EUR/USD at invoice maturity
2. **Tariff Shocks**: 70% no tariff, 20% 15% tariff, 10% 25% tariff
3. **Metrics**: VaR(95%), CVaR(95%), probability of loss, expected loss
4. **Hedge Decision**: Linear ramp between configurable thresholds (10%–20% VaR%)

## Project Structure

```
tariff-hedge-sim/
├── config.yaml                  # All configurable parameters
├── src/
│   ├── config_loader.py         # YAML config reader
│   ├── generator.py             # Invoice generator
│   ├── ingest_bronze.py         # Bronze layer ingestion
│   ├── simulate_risk.py         # Monte Carlo simulation
│   └── generate_alerts.py       # Alert JSON writer
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/             # Bronze → staging views
│   │   ├── silver/              # Cleaned invoices
│   │   └── gold/                # Enriched risk results
│   └── tests/                   # Custom dbt assertions
├── airflow/dags/
│   └── tariff_hedge_dag.py      # DAG: generate → bronze → silver → sim → gold → alerts
├── docker/grafana/              # Grafana provisioning + dashboards
├── data/                        # Local storage (bronze/silver/gold/alerts)
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Quick Start

### With Docker (recommended)

```bash
docker-compose up --build -d
```

- **Airflow UI**: http://localhost:8080 (admin / admin)
- **Grafana**: http://localhost:3000 (admin / admin)

Trigger the DAG manually from the Airflow UI or wait for the daily schedule.

### Local Development (without Docker)

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run pipeline steps manually
python -m src.generator
python -m src.ingest_bronze

# 4. Run dbt
cd dbt_project
dbt run --select staging silver --profiles-dir .
cd ..

# 5. Simulate risk
python -m src.simulate_risk

# 6. Run gold layer + tests
cd dbt_project
dbt run --select gold --profiles-dir .
dbt test --profiles-dir .
cd ..

# 7. Generate alerts
python -m src.generate_alerts
```

## Configuration

All parameters are in `config.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `random_seed` | 42 | Reproducibility seed |
| `simulation.num_paths` | 10,000 | Monte Carlo paths |
| `fx.spot_rate` | 1.0840 | EUR/USD spot |
| `fx.forward_rate` | 1.0860 | EUR/USD forward |
| `fx.annualized_volatility` | 0.08 | 8% annual vol |
| `hedge.threshold` | 10.0 | VaR% below = no hedge |
| `hedge.max_threshold` | 20.0 | VaR% above = full hedge |

## Grafana Dashboard Panels

1. **Portfolio VaR (95%) by Invoice** — bar chart of downside risk per invoice
2. **Hedge Ratio Distribution** — bar chart showing recommended hedge amounts
3. **VaR % vs Threshold** — gauge with green/yellow/red zones
4. **Probability of Loss > 10%** — stat panel per invoice
5. **Recommendations Summary** — table with all key metrics and recommendation text

## dbt Tests

- `not_null` on all key columns
- `unique` on invoice_uuid (staging)
- Custom: `assert_usd_amount_positive`
- Custom: `assert_horizon_days_valid`
- Custom: `assert_hedge_ratio_bounded`

Generate dbt docs: `cd dbt_project && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .`
