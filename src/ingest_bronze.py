"""
Bronze ingestion – copies raw CSV from tmp to the bronze layer.

Bronze is append-only and partitioned by run_date.
Original data is never modified.
"""

import logging
import shutil
from datetime import date
from pathlib import Path

from src.config_loader import load_config, resolve_path

logger = logging.getLogger(__name__)


def ingest_to_bronze(run_date: date | None = None, config_path: Path | None = None) -> Path:
    """Copy the generated CSV into data/bronze/run_date=YYYY-MM-DD/.

    Returns the path to the copied file.
    """
    cfg = load_config(config_path)
    run_date = run_date or date.today()

    tmp_dir = resolve_path(cfg, "tmp")
    src_file = tmp_dir / f"invoices_{run_date}.csv"
    if not src_file.exists():
        raise FileNotFoundError(f"No generated file found at {src_file}")

    bronze_dir = resolve_path(cfg, "bronze") / f"run_date={run_date}"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    dest_file = bronze_dir / src_file.name

    shutil.copy2(src_file, dest_file)
    logger.info("Bronze ingested: %s -> %s", src_file, dest_file)
    return dest_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    out = ingest_to_bronze()
    print(f"Bronze file -> {out}")
