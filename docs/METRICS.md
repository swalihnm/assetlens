# Metric dictionary (kept in sync with code: `benchmark/metrics.py`, `pricing/mandate.py`, `forecast/bridges.py`)

| Metric | Formula | Notes |
|---|---|---|
| Average AUM | reported average where disclosed (TROW from 2023-Q2, IVZ), else (begin + end) / 2 | `aum_avg_method` column states which |
| Fee yield (bps) | quarterly fees x 4 / average AUM x 10,000 | GS: management and other fees / avg AUS; BLK: base fees + securities lending; TROW: investment advisory fees; IVZ: investment management fees (gross) |
| Fee yield T4Q | sum of 4 quarters of fees / mean of 4 average AUMs x 10,000 | used for league tables and the compression regression |
| Organic growth (ann.) | net flows x 4 / beginning AUM | T4Q: 4-quarter flows / AUM four quarters earlier |
| Market impact % | (end - begin - net flows) / begin | BLK: residual by construction; GS/TROW/IVZ: reported market + FX + acquisitions |
| Operating margin | operating income / net revenues | GS: segment pre-tax earnings (after provision); BLK/TROW/IVZ: GAAP operating income |
| Compensation ratio | compensation / net revenues | GS annual only (FY2022-25, ASU 2023-07) |
| Efficiency ratio | operating expenses / net revenues | |
| Operating leverage (YoY) | %change net revenues - %change operating expenses | |
| Contribution margin | revenue - direct costs - provision | synthetic businesses |
| Fully allocated profit | contribution margin - allocated shared costs | five methods |
| Break-even fee (marginal / fully allocated) | effective bps on year-1 average AUM at which profit = 0 (tier schedule scaled by lambda, solved with brentq) | lifetime variant: survival-weighted NPV = 0 |
| Mandate LTV | sum_t S(t) x profit_t / (1+r)^t - onboarding; Weibull S, mid-year | |
| PVM | Volume = (A1-A0) y0; Mix = A1 sum (w1-w0) y0; Rate = A1 sum w1 (y1-y0); sums exactly to the fee change | unit and property tested |
| Growth case | NPV, IRR (with terminal value), payback, discounted payback, break-even year | explicit-period NPV also reported |
