/*
    Silver layer: cleaned, validated invoices with traceability columns.

    Adds:
      - ingestion_timestamp
      - is_valid flag (basic quality checks)
      - is_latest (true for the most recent row per invoice_uuid)
*/

{{ config(materialized='table') }}

with base as (

    select
        invoice_uuid,
        invoice_id,
        usd_amount,
        invoice_date,
        due_date,
        horizon_days,
        source_file_name,
        current_timestamp as ingestion_timestamp,

        -- validation flags
        case
            when usd_amount > 0
                 and due_date > invoice_date
                 and horizon_days >= 90
            then true
            else false
        end as is_valid

    from {{ ref('stg_bronze_invoices') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by invoice_uuid
            order by ingestion_timestamp desc
        ) as rn

    from base

)

select
    invoice_uuid,
    invoice_id,
    usd_amount,
    invoice_date,
    due_date,
    horizon_days,
    source_file_name,
    ingestion_timestamp,
    is_valid,
    case when rn = 1 then true else false end as is_latest

from ranked
