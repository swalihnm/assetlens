# DATA GAPS

| ID | Item | Reason | Status |
|----|------|--------|--------|
| G1 | GS AWM quarterly revenue/pre-tax/flows 2019Q1-2021Q4 (AWM perimeter) | Perimeter re-based in FY2022 10-K; only legacy "Asset Management" quarterlies exist (different perimeter). AWM annual FY2020/21 revenue and pre-tax available. | Not fillable from filings |
| G2 | GS AWM Q3 2026 operating expenses & pre-tax | 10-Q not yet filed; `make refresh` (and the AssetLensRefresh scheduled task) fills it automatically once EDGAR has it | Automated |
| G3 | GS AWM quarterly compensation | ASU 2023-07 segment comp only in 10-K (annual 2022-25) | Annual only |
| G4 | GS AWM Q4 2025 derived on mixed vintage | Resolved automatically by the same refresh (Q3-26 10-Q carries recast 9M-25) | Automated |
| G5 | GS AWM 2019Q1-2022Q3 AUS roll-forward on AWM basis | Re-based; legacy roll-forward not comparable. Total-AUS ending balance IS available 2018-12 → 2026-09 | Partial |
| G6 | TROW AUM roll-forward 2020-Q3 and 2021-Q4 | RESOLVED: 'Acquired AUM' / 'Acquired fee-basis AUM' rows (Legg-Mason-style acquisitions) are now treated as other changes; all 30 quarters chain | Closed |
| G7 | BLK begin/market/FX split | Releases give net flows, ending AUM and base fees only; market impact stored as residual | By construction |
| G8 | TROW quarterly releases before 2023-05 | Q1-Q3 earnings were not furnished on 8-K; 10-Q tables used (P&L and AUM) | Covered via 10-Q |
| G9 | Peer Q3-2026 for TROW and IVZ | Not yet reported (late Oct) | Re-run after release |
| G10 | MS, JPM, BEN peers | Phase 2 | Not started |
| G11 | ICE BofA bond total-return indices before Oct-2023 | FRED now serves ~3 years only (licensing). Bond return proxy = y10/4 - 6.5 x dy (corr 0.955 with ICE over 11 overlapping quarters) | Proxy used in M5 |
| G12 | MS Investment Management P&L and AUM | RESOLVED: P&L 2019-Q1 to 2026-Q2 (2019-20 layout identified by size; Q4s derived as FY - Q1..Q3, so segment recasts between filings can distort derived Q4s, e.g. Q4 2019) and AUM roll-forward 2021-Q1 to 2026-Q2 in three layouts | Closed with caveat |
| G13 | JPM AWM segment P&L | RESOLVED for 2019-26: Q4 2019-22 derived as FY - Q1..Q3 (FY from 10-K, quarters from 10-Qs; segment recasts between filings can distort derived Q4s, e.g. Q4 2020). Fee line relabelled in 2023 (definitional break) | Closed with caveat |
| G14 | BEN AUM roll-forward before 2020-Q3 | RESOLVED: 'Long-term' flow detail rows excluded (already inside Net flows); all 30 quarters chain. Operating income missing in two fiscal-Q4 releases | Closed |
| G15 | MS Wealth Management client assets / net new assets | Not parsed (WM P&L only, ticker MSWM) | Open |
