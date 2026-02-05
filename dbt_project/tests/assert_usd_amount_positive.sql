-- Custom test: all silver invoices must have positive USD amounts.

select invoice_uuid, usd_amount
from {{ ref('silver_invoices') }}
where usd_amount <= 0
