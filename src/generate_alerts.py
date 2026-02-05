"""
Alert generator – writes one JSON file per invoice to data/alerts/YYYY-MM-DD/.

Alerts contain the full risk summary for each invoice,
suitable for Slack/email/dashboard consumption.
"""

import json
import logging
from datetime import date
from pathlib import Path

import duckdb

from src.config_loader import load_config, resolve_path

logger = logging.getLogger(__name__)


def generate_alerts(run_date: date | None = None, config_path: Path | None = None) -> list[Path]:
    """Read gold results and emit one JSON alert per invoice.

    Returns list of paths to generated alert files.
    """
    cfg = load_config(config_path)
    run_date = run_date or date.today()

    db_path = resolve_path(cfg, "silver").parent / "warehouse.duckdb"
    con = duckdb.connect(str(db_path), read_only=True)

    try:
        df = con.execute(
            "SELECT * FROM gold_risk_results WHERE is_latest = true"
        ).fetchdf()
    finally:
        con.close()

    if df.empty:
        logger.warning("No gold results to generate alerts for")
        return []

    alerts_dir = resolve_path(cfg, "alerts") / run_date.isoformat()
    alerts_dir.mkdir(parents=True, exist_ok=True)

    alert_paths = []
    for _, row in df.iterrows():
        alert = {
            "invoice_uuid": row["invoice_uuid"],
            "invoice_id": row["invoice_id"],
            "usd_amount": float(row["usd_amount"]),
            "invoice_date": str(row["invoice_date"]),
            "due_date": str(row["due_date"]),
            "horizon_days": int(row["horizon_days"]),
            "hedged_eur": float(row["hedged_eur"]),
            "var_95_eur": float(row["var_95_eur"]),
            "cvar_95_eur": float(row["cvar_95_eur"]),
            "var_percentage": float(row["var_percentage"]),
            "hedge_ratio": float(row["hedge_ratio"]),
            "recommendation": row["recommendation"],
            "prob_loss_positive": float(row["prob_loss_positive"]),
            "expected_loss_eur": float(row["expected_loss_eur"]),
            "prob_loss_gt_10pct": float(row["prob_loss_gt_10pct"]),
            "min_loss": float(row["min_loss"]),
            "max_loss": float(row["max_loss"]),
            "median_loss": float(row["median_loss"]),
            "simulation_timestamp": str(row["simulation_timestamp"]),
            "run_date": run_date.isoformat(),
        }

        alert_path = alerts_dir / f"{row['invoice_uuid']}.json"
        with open(alert_path, "w") as f:
            json.dump(alert, f, indent=2)
        alert_paths.append(alert_path)

    logger.info("Generated %d alerts in %s", len(alert_paths), alerts_dir)
    return alert_paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    paths = generate_alerts()
    for p in paths:
        print(f"Alert -> {p}")
