# M4 Peer benchmarking

**Method.** Metrics per `docs/METRICS.md` for 7 companies (GS AWM, BLK, TROW, IVZ, MS Investment Management, JPM Asset & Wealth Management, BEN): fee yield, organic growth, market impact, margin, comp ratio, operating leverage, trailing four quarters, peer z-scores. Fee compression = OLS of T4Q fee yield on time with HAC errors; AUM decomposition into flows vs market/FX/other since 2022. A `comparability_flags` table documents definition differences per company.

**Outputs.** `mart_peer_benchmark`, `mart_fee_compression`, `mart_aum_decomposition`, `comparability_flags`, charts.

**Results and validation.** Fee yield T4Q: BEN 43.8, TROW 38.6, JPM 35.1, GS 34.8, MS 33.4, IVZ 23.9, BLK 15.6 bps. Fee-yield trends bps/yr: IVZ -2.89, JPM -1.77, BEN -1.38, TROW -1.27, MS -1.22, BLK -0.35, GS -0.33 (all significant). Organic growth T4Q: GS 14.9%, MS 10.1%, JPM 9.3%, IVZ 7.6%, BLK 6.5%, BEN 3.8%, TROW -3.2%.

**Limitations.** Not perfectly like-for-like: AUS vs AUM, gross vs net fees (IVZ, BEN), GAAP vs adjusted margins, segment vs firm. JPMorgan relabelled its fee line in 2023 (break in fee yield). Goldman's T4Q margin lags a quarter until its Q3-2026 10-Q is filed.
