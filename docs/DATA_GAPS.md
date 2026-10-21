# DATA GAPS

| ID | Item | Reason | Status |
|----|------|--------|--------|
| G1 | GS AWM quarterly revenue/pre-tax/flows 2019Q1-2021Q4 (AWM perimeter) | Perimeter re-based in FY2022 10-K; only legacy "Asset Management" quarterlies exist (different perimeter). AWM annual FY2020/21 revenue and pre-tax available. | Not fillable from filings |
| G2 | GS AWM Q3 2026 operating expenses & pre-tax | 10-Q not yet filed (due ≈ 30 Oct 2026); earnings release exhibit only has revenue lines + AUS | Re-run `run_gs` after the 10-Q |
| G3 | GS AWM quarterly compensation | ASU 2023-07 segment comp only in 10-K (annual 2022-25) | Annual only |
| G4 | GS AWM Q4 2025 derived on mixed vintage | FY2025 10-K recast vs 9M original | Auto-resolves after Q3'26 10-Q |
| G5 | GS AWM 2019Q1-2022Q3 AUS roll-forward on AWM basis | Re-based; legacy roll-forward not comparable. Total-AUS ending balance IS available 2018-12 → 2026-09 | Partial |
| G6 | TROW AUM roll-forward 2020-Q3 and 2021-Q4 | 10-Q total table fails closure (2020-Q3); Q4-2021 release table not parseable | Dropped by chain filter; end balances exist for neighbours |
| G7 | BLK begin/market/FX split | Releases give net flows, ending AUM and base fees only; market impact stored as residual | By construction |
| G8 | TROW quarterly releases before 2023-05 | Q1-Q3 earnings were not furnished on 8-K; 10-Q tables used (P&L and AUM) | Covered via 10-Q |
| G9 | Peer Q3-2026 for TROW and IVZ | Not yet reported (late Oct) | Re-run after release |
| G10 | MS, JPM, BEN peers | Phase 2 | Not started |
| G11 | ICE BofA bond total-return indices before Oct-2023 | FRED now serves ~3 years only (licensing). Bond return proxy = y10/4 - 6.5 x dy (corr 0.955 with ICE over 11 overlapping quarters) | Proxy used in M5 |
| G12 | MS Investment Management AUM roll-forward before 2024-Q1 | 2024-26 layouts parsed (6- and 7-column); 2021-23 layout not parsed; P&L parsed from 2021 | Open |
| G13 | JPM AWM segment P&L before 2023-Q1 | 2023-26 parsed (anchored on 'Global Private Bank'); 2019-22 layout not parsed; AUM roll-forward complete 2019-26 | Open |
| G14 | BEN AUM roll-forward before 2020-Q3; operating income in two fiscal-Q4 releases | Older/Q4 release layouts differ | Open |
| G15 | MS Wealth Management client assets / net new assets | Not parsed (WM P&L only, ticker MSWM) | Open |
