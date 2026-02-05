-- Custom test: hedge_ratio must be between 0 and 1 inclusive.

select invoice_uuid, hedge_ratio
from {{ ref('gold_risk_results') }}
where hedge_ratio < 0 or hedge_ratio > 1
