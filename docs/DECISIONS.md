# DECISIONS & verification log

Format: date · decision · why.

## 2026-10-21 · Day 1 verification
- **CIKs verified** against each submissions JSON: GS 0000886982 (GOLDMAN SACHS GROUP INC), BLK old 0001364742
  (now named "BlackRock Finance, Inc.", filings 2019-01 → 2024-10-01), BLK new 0002012383 (from 2024-10-11),
  TROW 0001113169, IVZ 0000914208. MS/JPM/BEN deferred to Phase 2 (CIKs in `config/peers.yaml`, unverified).
- **Manifest**: `data/raw/manifest.csv` – 593 10-K/10-Q/8-K filings since 2019-01-01 (GS 188, BLK 130 across both CIKs,
  TROW 91, IVZ 184). Latest GS 10-Q on file is Q2 2026; the Q3 2026 10-Q is not yet filed (today 2026-10-21), so
  Q3 2026 comes from the 8-K Exhibit 99.1 earnings release (revenue lines + AUS roll-forward only).
- **XBRL via inline-XBRL/HTML tables instead of Arelle (deviation).** GS MD&A tables (segment P&L, AUS roll-forward,
  AUS by asset class) are clean HTML, so Phase 1 parses them directly with BeautifulSoup/lxml and stores table index +
  row label + raw row text as provenance. Dimensional iXBRL (Arelle) remains an optional cross-check, not done yet.
- **FRED**: public `fredgraph.csv` endpoint works without a key. All 8 series download. Quarterly returns computed for
  index-level series (SP500, ICE BofA CC and HY total-return indices), quarterly averages for rates/FX/CPI.
  The partial quarter ending 2026-12-31 is not complete and must be excluded from analysis.
- **SEC User-Agent** read from `SEC_USER_AGENT` in `.env` (gitignored). Throttle 8 req/s (< 10 limit), disk cache.

## GS AWM perimeter change (important for comparability)
- Before the FY2022 10-K (filed 2023-02), GS reported "Asset Management" (2020-22) / "Investment Management" (2019)
  with a narrower perimeter. From the FY2022 10-K the segment is **Asset & Wealth Management** (adds wealth/private
  banking and lending, **AUS total re-based**; e.g. Dec-2021 AUS 2,470bn vs legacy roll-forward ending 1,719bn).
- Decision: facts carry a `perimeter` tag (`legacy_AM` vs `AWM`, by filing date ≥ 2023-02-01). Marts use **AWM only**.
  Recast comparatives in 2023 10-Qs give a consistent AWM quarterly series **from 2022 Q1**; FY2020 and FY2021 are
  available as annual AWM figures (from the FY2022 10-K). 2019 – 2021 quarterly AWM flows/revenue: not available → DATA_GAPS.
- Total AUS (all of GS) ending balances are available from 2018-12 in a consistent definition; used as the long series.

## Restatements
- All filing vintages are kept (`gs_raw_facts.csv`), latest-filed value used (`gs_facts_latest.csv`), changes logged in
  `gs_restatement_log.csv` (203 rows). Example: Q1 2025 AWM net revenues 3,679 originally → 3,711 recast in Q1 2026 10-Q
  (Investments line re-defined as one line; "Equity investments" + "Debt investments" combined as `rev_investments`).

## Q4 derivation
- Q4 = FY − 9M YTD (10-K minus Q3 10-Q YTD). **Caveat:** Q4 2025 mixes the post-recast FY2025 10-K with the pre-recast
  9M-2025 YTD; the quarter is internally consistent (lines sum) but may be overstated by the recast delta of Q1-Q3 2025
  (≈ +0.1bn). It resolves automatically once the Q3 2026 10-Q (≈30 Oct 2026) is ingested. Flagged in DATA_GAPS.

## Segment compensation (ASU 2023-07)
- GS FY2024 and FY2025 10-Ks tag AWM **Compensation and benefits expenses** and **Other operating expenses** (FY2022-FY2025
  shown). Segment comp ratio is therefore available **annually for 2022-2025 only**; not in 10-Q segment tables → no
  quarterly AWM comp ratio (DATA_GAPS).

## M5 market sensitivity (2026-10-21)
- Regress quarterly market impact % of beginning AUM on S&P 500 quarterly return and a **duration-based bond proxy** (HC3 robust errors). ICE BofA series from FRED cover only Oct-2023 onward.
- Result: TROW equity beta 0.85 (R2 0.98), BLK 0.66 (R2 0.95), IVZ 0.64, GS 0.07 (not significant, n=19). GS's disclosed equity+alternatives share is 28-40%, so the GS estimate is BELOW what the mix implies: GS market appreciation includes FX, third-party-distributed assets and lagged alternative marks, and has only 19 post-recast quarters. Treat the GS beta as inconclusive, not as a finding.
- GS lending revenue vs policy rate: 0.11 pp QoQ growth per 1 pp change in fed funds (p = 0.39, n = 18) - not distinguishable from zero; the scenario model's rate beta (0.35) remains an assumption.

## M6 Monte Carlo and backtest (2026-10-21)
- Monte Carlo: 10,000 paths; moving-block bootstrap (block = 2 quarters) of joint S&P 500 / bond-proxy quarterly returns from the FRED window (39 quarters, 2016-2026, a strong-equity era, so the median path is above the deterministic base: Q8 margin P50 32.0% vs 29.3%). Incentive fees, Investments and organic flows are linked to the equity path plus noise (assumptions in `montecarlo.stochastic_shocks`). P(Q8 margin < 25%) = 3.2%; P(any quarter < 25%) = 13.1%.
- Backtest target = GS AWM management & other fees (the structurally modelled line), 8 origins, horizons 1-4, 26 forecast/actual pairs. MAPE: model with realised markets 2.5%, model with assumed markets 3.5%, best baseline (drift) 4.5%, naive 8.1%, seasonal naive 12.6%. So the conditional model cuts error 44% vs the best baseline and the unconditional 22%. Sample is small (26 pairs, 18 quarters of AWM history) - indicative only. Runs logged to MLflow (sqlite, data/mlflow.db).

## M10 Monte Carlo and real option (2026-10-21)
- Random drivers: mature AUM/advisor (lognormal, sd 0.30), net revenue bps (N, sd 8), ramp midpoint U(1,2.5), attrition, hiring achievement Beta(8.5,1.5), market path N(6%, 14%).
- Full-entry mean NPV ~$275m, P(loss) ~9%. Staged entry (3-advisor pilot, expand if year-2 AUM clears a gate, expansion delayed 1-2 years, pilot advisors not reused) has NEGATIVE option value in all 6 gate/delay settings (-$55m to -$167m): the gate screens out good paths (false negatives) and delays a project that is positive in ~90% of paths. Staging reduces the worst-case outlay, not expected value. Result depends on the illustrative assumptions and terminal-value weight.
- Earlier deck wording ("staged entry advisable") was replaced with this finding.
