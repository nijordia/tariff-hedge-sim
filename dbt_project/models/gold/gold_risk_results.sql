/*
    Gold layer: risk simulation results joined with invoice metadata.

    Reads the simulation output Parquet and enriches it.
    Tracks is_latest per invoice_uuid so we keep history.
*/

{{ config(materialized='table') }}

with sim_results as (

    select *
    from read_parquet('../data/silver/simulation_results.parquet')

),

invoices as (

    select *
    from {{ ref('silver_invoices') }}
    where is_valid = true
      and is_latest = true

),

enriched as (

    select
        s.invoice_uuid,
        i.invoice_id,
        i.usd_amount,
        i.invoice_date,
        i.due_date,
        i.horizon_days,
        s.hedged_eur,
        s.var_95_eur,
        s.cvar_95_eur,
        s.var_percentage,
        s.hedge_ratio,
        s.recommendation,
        s.prob_loss_positive,
        s.expected_loss_eur,
        s.prob_loss_gt_10pct,
        s.min_loss,
        s.max_loss,
        s.median_loss,
        s.simulation_timestamp,
        s.run_date,
        row_number() over (
            partition by s.invoice_uuid
            order by s.simulation_timestamp desc
        ) as rn

    from sim_results s
    inner join invoices i
        on s.invoice_uuid = i.invoice_uuid

)

select
    invoice_uuid,
    invoice_id,
    usd_amount,
    invoice_date,
    due_date,
    horizon_days,
    hedged_eur,
    var_95_eur,
    cvar_95_eur,
    var_percentage,
    hedge_ratio,
    recommendation,
    prob_loss_positive,
    expected_loss_eur,
    prob_loss_gt_10pct,
    min_loss,
    max_loss,
    median_loss,
    simulation_timestamp,
    run_date,
    case when rn = 1 then true else false end as is_latest

from enriched
