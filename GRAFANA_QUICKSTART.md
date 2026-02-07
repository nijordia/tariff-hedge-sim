# Grafana Dashboard - Quick Start

Get your dashboard up and running in 5 minutes!

## 🚀 Quick Steps

### 1. Rebuild Docker (one-time)
```bash
# Install new dependency (psycopg2-binary)
docker-compose build
docker-compose up -d
```

### 2. Run the Pipeline
```bash
# Access Airflow UI
open http://localhost:8080
# Login: admin / admin

# Trigger DAG: tariff_hedge_pipeline
# Wait for all tasks to complete (including new load_grafana task)
```

### 3. Access Grafana
```bash
# Open Grafana
open http://localhost:3000
# Login: admin / admin
```

### 4. Add Data Source
1. Click **Settings** (⚙️) → **Data Sources**
2. Click **Add data source** → Select **PostgreSQL**
3. Fill in:
   - Name: `TariffHedgeSim`
   - Host: `postgres:5432`
   - Database: `airflow`
   - User: `airflow`
   - Password: `airflow`
   - SSL Mode: `disable`
4. Click **Save & Test** → Should show ✅

### 5. Create Dashboard
1. Click **Dashboards** → **New Dashboard**
2. Click **Add visualization**
3. Select **TariffHedgeSim** datasource
4. Copy-paste queries from `GRAFANA_SETUP.md`

## 📊 Essential Panels (Copy-Paste Queries)

### Panel 1: Top Risks (Bar Chart)
```sql
SELECT
  invoice_id as "Invoice",
  var_95_eur as "VaR €"
FROM dashboard.gold_risk_results
ORDER BY var_95_eur DESC
LIMIT 20
```

### Panel 2: Average VaR (Gauge)
```sql
SELECT AVG(var_percentage) as "Avg VaR %"
FROM dashboard.gold_risk_results
```
- Thresholds: Green 0%, Yellow 5%, Red 10%

### Panel 3: Risk Summary (Table)
```sql
SELECT
  invoice_id as "Invoice ID",
  ROUND(var_95_eur, 2) as "VaR 95% €",
  ROUND(var_percentage, 2) as "VaR %",
  ROUND(hedge_ratio * 100, 1) as "Hedge %",
  recommendation as "Recommendation"
FROM dashboard.gold_risk_results
ORDER BY var_percentage DESC
```

## ✅ Verify It Works

1. Check data loaded:
   ```bash
   docker exec -it tariff-hedge-sim-postgres-1 psql -U airflow -d airflow -c "SELECT COUNT(*) FROM dashboard.gold_risk_results;"
   ```
   Should return number of invoices (not 0).

2. Refresh Grafana dashboard → See live data!

## 🔄 Update Data

Data auto-updates when Airflow DAG runs (daily schedule or manual trigger).

To force update:
```bash
# In Airflow UI, trigger: load_grafana task only
# OR run full pipeline
```

## 📖 Full Documentation

See `GRAFANA_SETUP.md` for:
- All 6 panel configurations with screenshots
- Advanced features (time filters, annotations)
- Troubleshooting guide
- Performance tips

## 🆘 Troubleshooting

**No data in dashboard?**
```bash
# Check if load_grafana task succeeded in Airflow UI
# Check logs:
docker-compose logs airflow-webserver | grep load_grafana
```

**Connection failed?**
- Use `postgres` as host (NOT `localhost`)
- Check credentials match `.env` file

**Grafana won't load?**
```bash
docker-compose restart grafana
docker-compose logs grafana
```

---

**🎉 Done!** You now have a live business intelligence dashboard for FX risk monitoring.
