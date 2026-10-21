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
