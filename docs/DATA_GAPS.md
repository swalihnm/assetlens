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
