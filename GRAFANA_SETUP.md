# Grafana Dashboard Setup Guide

Complete step-by-step instructions for setting up the tariff-hedge-sim Grafana dashboard.

## Prerequisites

- Docker Compose running (`docker-compose up -d`)
- Pipeline executed at least once (Airflow DAG completed)
- Data loaded into Postgres (`load_grafana` task succeeded)

## Step 1: Access Grafana

1. **Open Grafana in your browser:**
   ```
   http://localhost:3000
   ```

2. **Login with credentials:**
   - Username: `admin`
   - Password: `admin` (or what you set in `.env`)

3. **Skip password change** (optional for local dev)

## Step 2: Add Postgres Data Source

1. **Navigate to:** Settings (⚙️) → Data Sources

2. **Click:** "Add data source"

3. **Select:** PostgreSQL

4. **Configure connection:**
   ```
   Name: TariffHedgeSim
   Host: postgres:5432
   Database: airflow
   User: airflow
   Password: airflow
   SSL Mode: disable
   Version: 12+
   ```

5. **Click:** "Save & Test"

6. **Verify:** You should see ✅ "Database Connection OK"

## Step 3: Create New Dashboard

1. **Navigate to:** Dashboards → New Dashboard

2. **Click:** "Add visualization"

3. **Select datasource:** TariffHedgeSim

4. **You're ready to add panels!**

---

## Panel Configurations

### Panel 1: VaR 95% per Invoice (Bar Chart)

**Purpose:** Shows Value-at-Risk for each invoice in descending order.

**Configuration:**
- **Type:** Bar chart
- **Title:** "Top 20 Invoices by VaR 95%"
- **Query:**
  ```sql
  SELECT
    invoice_id as "Invoice",
    var_95_eur as "VaR €"
  FROM dashboard.gold_risk_results
  ORDER BY var_95_eur DESC
  LIMIT 20
  ```
- **Panel Options:**
  - Orientation: Horizontal
  - Show values: On bar
  - Bar width: 0.8
- **Color scheme:** Red gradient (Reds)
- **Axes:**
  - X-axis label: "Value at Risk (€)"
  - Y-axis label: "Invoice ID"

---

### Panel 2: Hedge Ratio Distribution (Bar Chart)

**Purpose:** Shows how many invoices fall into each hedge category.

**Configuration:**
- **Type:** Bar chart (or Pie chart)
- **Title:** "Hedge Coverage Distribution"
- **Query:**
  ```sql
  SELECT
    CASE
      WHEN hedge_ratio = 0 THEN 'Unhedged (0%)'
      WHEN hedge_ratio < 0.5 THEN 'Partial (1-49%)'
      WHEN hedge_ratio < 1.0 THEN 'Mostly Hedged (50-99%)'
      ELSE 'Fully Hedged (100%)'
    END as "Hedge Category",
    COUNT(*) as "Count"
  FROM dashboard.gold_risk_results
  GROUP BY 1
  ORDER BY
    CASE
      WHEN hedge_ratio = 0 THEN 1
      WHEN hedge_ratio < 0.5 THEN 2
      WHEN hedge_ratio < 1.0 THEN 3
      ELSE 4
    END
  ```
- **Panel Options:**
  - Show values: On
  - Color by: Field (Hedge Category)
- **Color scheme:** Green to Red (RdYlGn reversed)

**Alternative as Pie Chart:**
- Change visualization to "Pie chart"
- Legend: Show, position right
- Calculate: Total

---

### Panel 3: Average VaR Percentage (Gauge)

**Purpose:** Shows portfolio-wide average VaR% with color-coded risk zones.

**Configuration:**
- **Type:** Gauge
- **Title:** "Average Portfolio VaR %"
- **Query:**
  ```sql
  SELECT
    AVG(var_percentage) as "Avg VaR %"
  FROM dashboard.gold_risk_results
  ```
- **Thresholds:**
  - Base: Green (0%)
  - Yellow: 5%
  - Red: 10%
- **Value options:**
  - Unit: Percent (0-100)
  - Decimals: 2
  - Show threshold labels: Yes
  - Show threshold markers: Yes
- **Gauge:**
  - Max: 20 (or auto)
  - Show: Calculate, all values

---

### Panel 4: Probability of Loss > 10% (Stat)

**Purpose:** Shows the average probability across all invoices of experiencing >10% loss.

**Configuration:**
- **Type:** Stat
- **Title:** "Avg Probability: Loss > 10%"
- **Query:**
  ```sql
  SELECT
    AVG(prob_loss_gt_10pct) * 100 as "Probability %"
  FROM dashboard.gold_risk_results
  ```
- **Thresholds:**
  - Base: Green (0%)
  - Yellow: 20%
  - Orange: 40%
  - Red: 60%
- **Value options:**
  - Unit: Percent (0-100)
  - Decimals: 1
- **Graph mode:** None (or Area for sparkline)
- **Text mode:** Value and name

---

### Panel 5: Recommendations Summary (Table)

**Purpose:** Detailed table of all invoices with risk metrics and recommendations.

**Configuration:**
- **Type:** Table
- **Title:** "Invoice Risk Summary"
- **Query:**
  ```sql
  SELECT
    invoice_id as "Invoice ID",
    TO_CHAR(invoice_date, 'YYYY-MM-DD') as "Date",
    ROUND(invoice_value_eur, 2) as "Invoice €",
    ROUND(hedged_eur, 2) as "Hedged €",
    ROUND(var_95_eur, 2) as "VaR 95% €",
    ROUND(var_percentage, 2) as "VaR %",
    ROUND(hedge_ratio * 100, 1) as "Hedge %",
    ROUND(prob_loss_gt_10pct * 100, 1) as "P(Loss>10%)",
    recommendation as "Recommendation"
  FROM dashboard.gold_risk_results
  ORDER BY var_percentage DESC
  ```
- **Table options:**
  - Sortable columns: Yes
  - Filterable: Yes
  - Show header: Yes
  - Cell display mode: Auto
- **Column overrides:**
  - **VaR %**: Add cell background color
    - Base: Green (0)
    - Yellow: 5
    - Red: 10
  - **Recommendation**: Cell display mode = Color text
    - Map values: HEDGE_MORE → Red, MAINTAIN → Yellow, REDUCE_HEDGE → Green

---

### Panel 6: Total Exposure Metrics (Stat Panel Group)

**Purpose:** Show key aggregate metrics at a glance.

**Configuration:**
Create 4 separate Stat panels in a row:

#### 6a. Total Invoice Value
```sql
SELECT SUM(invoice_value_eur) as "Total Invoice Value €"
FROM dashboard.gold_risk_results
```
- Unit: Currency (EUR)
- Color: Blue

#### 6b. Total Hedged Amount
```sql
SELECT SUM(hedged_eur) as "Total Hedged €"
FROM dashboard.gold_risk_results
```
- Unit: Currency (EUR)
- Color: Green

#### 6c. Total VaR 95%
```sql
SELECT SUM(var_95_eur) as "Total VaR 95% €"
FROM dashboard.gold_risk_results
```
- Unit: Currency (EUR)
- Color: Red

#### 6d. Portfolio Hedge Ratio
```sql
SELECT
  ROUND(
    SUM(hedged_eur) / NULLIF(SUM(invoice_value_eur), 0) * 100,
    1
  ) as "Portfolio Hedge %"
FROM dashboard.gold_risk_results
```
- Unit: Percent (0-100)
- Color: Yellow

---

## Step 4: Arrange Dashboard Layout

1. **Drag panels** to arrange them logically:
   - Top row: 4 stat panels (6a-6d) - Total metrics
   - Second row: Gauge (Panel 3) + Stat (Panel 4)
   - Third row: Bar charts (Panel 1 + Panel 2)
   - Bottom: Full-width Table (Panel 5)

2. **Resize panels** by dragging corners

3. **Save dashboard:**
   - Click "Save dashboard" icon (top right)
   - Name: "Tariff Hedge Risk Dashboard"
   - Add description (optional)
   - Click "Save"

---

## Step 5: Dashboard Settings & Polish

### Add Time Range Filter (Optional)

If you add `invoice_date` filtering:

1. **Dashboard settings** → Variables → Add variable
2. **Type:** Query
3. **Query:**
   ```sql
   SELECT DISTINCT invoice_date
   FROM dashboard.gold_risk_results
   ORDER BY invoice_date DESC
   ```
4. **Multi-value:** Yes
5. **Include All option:** Yes

Then update queries to filter:
```sql
WHERE invoice_date = ANY(ARRAY['$invoice_date']::date[])
```

### Auto-refresh

1. **Dashboard settings** → Time options
2. **Auto refresh:** 1m, 5m, 15m, 30m, 1h
3. Recommended: 5m for dev, 15m for production

### Annotations (Optional)

Add annotations for pipeline runs:
- Data source: TariffHedgeSim
- Query:
  ```sql
  SELECT
    updated_at as time,
    'Pipeline Run' as text
  FROM dashboard.gold_risk_results
  ORDER BY updated_at DESC
  LIMIT 1
  ```

---

## Step 6: Test & Verify

1. **Trigger Airflow DAG** manually
2. **Wait for `load_grafana` task** to complete
3. **Refresh Grafana dashboard** (click refresh icon or use auto-refresh)
4. **Verify new data appears**

---

## Troubleshooting

### Issue: "Database Connection Failed"
**Solution:**
- Check Postgres is running: `docker ps | grep postgres`
- Verify credentials in `.env` match datasource config
- Use `postgres` as host (Docker service name), not `localhost`

### Issue: "Table does not exist"
**Solution:**
- Run `python src/load_grafana.py` locally once to create schema
- Or wait for Airflow DAG to run the `load_grafana` task

### Issue: "No data in dashboard"
**Solution:**
- Check if gold table has data:
  ```bash
  docker exec -it <airflow-container> bash
  cd /opt/airflow/project
  python -c "import duckdb; print(duckdb.connect('data/warehouse.duckdb').execute('SELECT COUNT(*) FROM gold_risk_results').fetchone())"
  ```
- Verify `load_grafana` task succeeded in Airflow UI

### Issue: Grafana shows old data
**Solution:**
- The load script uses `TRUNCATE` + reload, so data should always be fresh
- Check `updated_at` column in Postgres:
  ```sql
  SELECT MAX(updated_at) FROM dashboard.gold_risk_results;
  ```
- Manually refresh dashboard (Ctrl+R)

---

## Maintenance

### Updating the Dashboard
1. Data refreshes automatically when Airflow DAG runs
2. No manual intervention needed after initial setup
3. To force refresh: trigger `load_grafana` task in Airflow

### Adding New Panels
- Use `dashboard.gold_risk_results` table as source
- Available columns:
  - `invoice_id`, `invoice_date`, `invoice_value_eur`, `contract_value_usd`
  - `hedged_eur`, `var_95_eur`, `var_percentage`
  - `hedge_ratio`, `prob_loss_gt_10pct`, `recommendation`
  - `updated_at`

### Performance Tips
- Add indexes to Postgres for frequently filtered columns
- Limit large tables with `LIMIT` clause
- Use aggregations when displaying many rows

---

## Next Steps

✅ Dashboard is live!

**Optional enhancements:**
1. **Add loss distribution histogram** (see GRAFANA_ADVANCED.md)
2. **Set up alerting** (Grafana Alerts for high VaR)
3. **Export/share dashboard** (JSON export → version control)
4. **Add more metrics** (CVaR, Sharpe ratio, etc.)

---

## Quick Reference: URLs

- **Grafana:** http://localhost:3000
- **Airflow:** http://localhost:8080
- **Postgres:** localhost:5432 (credentials in `.env`)

---

**Need help?** Check logs:
```bash
# Airflow logs
docker-compose logs airflow-webserver

# Grafana logs
docker-compose logs grafana

# Postgres logs
docker-compose logs postgres
```
