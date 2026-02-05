-- Custom test: horizon_days must be >= 90 for valid invoices.

select invoice_uuid, horizon_days
from {{ ref('silver_invoices') }}
where is_valid = true
  and horizon_days < 90
