# M9 Mandate pricing

**Method.** Tiered fee schedule on average AUM; direct costs (PM and service FTE, trading, custody, data, onboarding, commission, capital charge) and ABC-allocated shared cost; break-even fee solved with Brent's method as a scaling of the tier schedule; minimum viable AUM; Weibull survival lifetime value; Monte Carlo over market paths; tornado; recommendation rule (never below marginal break-even; target fully allocated plus 15%). Served by the FastAPI `POST /mandate/price` and an Excel sheet.

**Outputs.** `pricing/mandate.py`, `pricing/inputs.py`, Excel `Mandate_Pricing`, API endpoint.

**Results and validation.** $1bn equity SMA: break-even 15.9 bps marginal vs 25.5 bps fully allocated; proposed 29.8 bps; minimum viable AUM $378m (marginal) / $623m (fully allocated); deterministic LTV $7.3m marginal / $3.3m fully allocated. Tests: profit is zero at every break-even, LTV falls with hazard, Weibull survival matches the stated hazard, Excel closed-form break-evens equal the Python solver.

**Limitations.** Cost inputs come from the synthetic M7/M8 tables. Peer fee-yield band is company-level, context only.
