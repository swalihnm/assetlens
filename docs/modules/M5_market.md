# M5 Market sensitivity

**Method.** Regress quarterly market impact (% of beginning AUM) on S&P 500 and a bond-return proxy (HC3 robust errors); rolling 12-quarter betas; asset-mix sanity check; Goldman lending revenue vs the policy rate. FRED now serves only about 3 years of the ICE BofA bond indices, so bond return is a duration proxy from the 10-year yield (y/4 - 6.5 x dy; correlation 0.955 with ICE over the 11 overlapping quarters).

**Outputs.** `mart_market_sensitivity`, `mart_market_beta_rolling`, residual diagnostics chart.

**Results and validation.** Equity beta (R2): TROW 0.85 (0.97), BLK 0.66 (0.95), JPM 0.41 (0.96), IVZ 0.64 (0.62). Goldman's equity beta (0.07, R2 0.48) is not significant and below what its asset mix implies; treated as inconclusive. Goldman lending revenue vs fed funds: not distinguishable from zero.

**Limitations.** Bond proxy is an approximation; market impact for BlackRock/Franklin/Morgan Stanley includes FX, acquisitions and distributions, which lowers fit.
