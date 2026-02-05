/*
    Staging: read all bronze CSV files into a single view.
    DuckDB's read_csv_auto handles schema inference.
    We add the source filename for traceability.
*/

{{ config(materialized='view') }}

select
    invoice_uuid,
    invoice_id,
    cast(usd_amount as double) as usd_amount,
    cast(invoice_date as date) as invoice_date,
    cast(due_date as date) as due_date,
    cast(horizon_days as integer) as horizon_days,
    filename as source_file_name
from read_csv_auto(
    '../data/bronze/run_date=*/invoices_*.csv',
    header = true,
    filename = true
)
