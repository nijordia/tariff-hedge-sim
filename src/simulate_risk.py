"""
Monte Carlo risk simulation for FX + tariff exposure.

For each invoice:
  1. Simulate 10,000 GBM paths for EUR/USD at maturity
  2. Sample tariff shocks per path
  3. Compute unhedged vs hedged EUR outcomes
  4. Calculate VaR, CVaR, and hedge recommendation

Output: Parquet file to data/silver/simulation_results.parquet
"""

import logging
from datetime import date, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from src.config_loader import load_config, resolve_path

logger = logging.getLogger(__name__)


def _run_simulation_for_invoice(
    row: dict,
    rng: np.random.Generator,
    cfg: dict,
) -> dict:
    """Run Monte Carlo simulation for a single invoice. Returns a dict of results."""
    fx = cfg["fx"]
    sim = cfg["simulation"]
    tariff_cfg = cfg["tariff"]
    hedge_cfg = cfg["hedge"]

    spot = fx["spot_rate"]
    forward = fx["forward_rate"]
    vol = fx["annualized_volatility"]
    num_paths = sim["num_paths"]

    usd_amount = row["usd_amount"]
    horizon_days = row["horizon_days"]
    T = horizon_days / 365.0

    # Risk-neutral drift so E[S_T] ≈ forward_rate
    mu = np.log(forward / spot) / T + (vol**2) / 2

    # GBM terminal values
    Z = rng.standard_normal(num_paths)
    S_T = spot * np.exp((mu - vol**2 / 2) * T + vol * np.sqrt(T) * Z)

    # Tariff shock sampling
    probs = [s["probability"] for s in tariff_cfg["scenarios"]]
    shocks = [s["shock"] for s in tariff_cfg["scenarios"]]
    shock_indices = rng.choice(len(shocks), size=num_paths, p=probs)
    shock_values = np.array([shocks[i] for i in shock_indices])

    effective_usd = usd_amount * (1 - shock_values)

    # Per-path outcomes
    unhedged_eur = effective_usd / S_T
    hedged_eur = usd_amount / forward  # fixed, certain
    loss_eur = hedged_eur - unhedged_eur  # positive = unhedged worse

    # Sort losses ascending (worst losses = most negative at start)
    sorted_losses = np.sort(loss_eur)

    # Risk metrics
    cutoff = int(0.05 * num_paths)
    var_95 = sorted_losses[cutoff]  # 5th percentile
    cvar_95 = sorted_losses[:cutoff].mean()

    var_percentage = (var_95 / hedged_eur) * 100

    prob_loss_positive = float((loss_eur > 0).mean())
    expected_loss = float(loss_eur.mean())
    prob_loss_gt_10pct = float((loss_eur > 0.10 * hedged_eur).mean())

    # Hedge decision
    threshold = hedge_cfg["threshold"]
    max_threshold = hedge_cfg["max_threshold"]
    hedge_ratio = min(1.0, max(0.0, (var_percentage - threshold) / (max_threshold - threshold)))

    if hedge_ratio == 0:
        recommendation = "No hedge recommended"
    else:
        recommendation = f"Hedge {int(hedge_ratio * 100)}% of the exposure"

    return {
        "invoice_uuid": row["invoice_uuid"],
        "hedged_eur": round(hedged_eur, 2),
        "var_95_eur": round(var_95, 2),
        "cvar_95_eur": round(cvar_95, 2),
        "var_percentage": round(var_percentage, 4),
        "hedge_ratio": round(hedge_ratio, 4),
        "recommendation": recommendation,
        "prob_loss_positive": round(prob_loss_positive, 4),
        "expected_loss_eur": round(expected_loss, 2),
        "prob_loss_gt_10pct": round(prob_loss_gt_10pct, 4),
        "min_loss": round(float(sorted_losses[0]), 2),
        "max_loss": round(float(sorted_losses[-1]), 2),
        "median_loss": round(float(np.median(loss_eur)), 2),
    }


def run_simulation(run_date: date | None = None, config_path: Path | None = None) -> Path:
    """Read silver invoices, simulate risk, write Parquet results.

    Returns path to the output Parquet file.
    """
    cfg = load_config(config_path)
    rng = np.random.default_rng(cfg["random_seed"])
    run_date = run_date or date.today()

    # Read silver invoices from DuckDB
    dbt_db_path = resolve_path(cfg, "silver").parent / "warehouse.duckdb"
    con = duckdb.connect(str(dbt_db_path), read_only=True)

    try:
        invoices_df = con.execute(
            "SELECT * FROM silver_invoices WHERE is_valid = true AND is_latest = true"
        ).fetchdf()
    finally:
        con.close()

    if invoices_df.empty:
        logger.warning("No valid invoices found in silver layer")
        return Path()

    logger.info("Simulating risk for %d invoices", len(invoices_df))
    sim_timestamp = datetime.utcnow().isoformat()

    results = []
    for _, row in invoices_df.iterrows():
        result = _run_simulation_for_invoice(row.to_dict(), rng, cfg)
        result["simulation_timestamp"] = sim_timestamp
        result["run_date"] = run_date.isoformat()
        results.append(result)

    results_df = pd.DataFrame(results)

    # Write to silver (intermediate simulation results consumed by gold dbt model)
    silver_dir = resolve_path(cfg, "silver")
    silver_dir.mkdir(parents=True, exist_ok=True)
    out_path = silver_dir / "simulation_results.parquet"

    # Append to existing results if file exists
    if out_path.exists():
        existing = pd.read_parquet(out_path)
        results_df = pd.concat([existing, results_df], ignore_index=True)

    results_df.to_parquet(out_path, index=False)
    logger.info("Wrote simulation results to %s (%d rows)", out_path, len(results_df))

    # Also write partitioned copy to gold
    gold_dir = resolve_path(cfg, "gold") / f"run_date={run_date}"
    gold_dir.mkdir(parents=True, exist_ok=True)
    gold_path = gold_dir / "simulation_results.parquet"
    pd.DataFrame(results).to_parquet(gold_path, index=False)
    logger.info("Wrote gold partition to %s", gold_path)

    return out_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    out = run_simulation()
    print(f"Simulation results -> {out}")
