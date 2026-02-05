"""
Invoice generator – creates 3-8 synthetic invoices per run.

Each invoice represents a Barcelona olive oil exporter selling to the US in USD.
Output: CSV written to data/tmp/ for downstream bronze ingestion.
"""

import csv
import logging
import uuid
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from src.config_loader import load_config, resolve_path

logger = logging.getLogger(__name__)


def generate_invoices(run_date: date | None = None, config_path: Path | None = None) -> Path:
    """Generate a batch of synthetic invoices and write to CSV.

    Returns the path to the generated CSV file.
    """
    cfg = load_config(config_path)
    rng = np.random.default_rng(cfg["random_seed"])
    run_date = run_date or date.today()

    inv_cfg = cfg["invoice"]
    num_invoices = rng.integers(inv_cfg["min_count"], inv_cfg["max_count"] + 1)
    logger.info("Generating %d invoices for run_date=%s", num_invoices, run_date)

    rows = []
    for i in range(1, num_invoices + 1):
        invoice_uuid = str(uuid.uuid4())
        invoice_id = f"EXP-{run_date:%Y%m%d}-{i:03d}"
        usd_amount = round(
            rng.uniform(inv_cfg["usd_amount_min"], inv_cfg["usd_amount_max"]), 2
        )
        horizon_days = int(
            rng.integers(inv_cfg["horizon_days_min"], inv_cfg["horizon_days_max"] + 1)
        )
        invoice_date = run_date.isoformat()
        due_date = (run_date + timedelta(days=horizon_days)).isoformat()

        rows.append(
            {
                "invoice_uuid": invoice_uuid,
                "invoice_id": invoice_id,
                "usd_amount": usd_amount,
                "invoice_date": invoice_date,
                "due_date": due_date,
                "horizon_days": horizon_days,
            }
        )

    # Write to tmp
    tmp_dir = resolve_path(cfg, "tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_path = tmp_dir / f"invoices_{run_date}.csv"

    fieldnames = [
        "invoice_uuid",
        "invoice_id",
        "usd_amount",
        "invoice_date",
        "due_date",
        "horizon_days",
    ]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Wrote %d invoices to %s", len(rows), out_path)
    return out_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    out = generate_invoices()
    print(f"Generated invoices -> {out}")
