# M14 Excel model

**Method.** openpyxl builder: 14 sheets, 1,151 live formulas, no hard-coded outputs. Scenario selector (data validation), AUM roll-forward by class, revenue, expenses, P&L, budget variance with PVM bridge, profitability with method selector, mandate pricing (closed-form break-evens), GCC case with location selector, sensitivity grid, benchmarks, and a Checks sheet. Blue = inputs, black = formulas, green = cross-sheet links.

**Outputs.** `outputs/excel/AssetLens_PnL_Model.xlsx`, `excel/parity.py`.

**Results and validation.** 13 integrity checks all equal zero. Parity test recalculates the workbook with a pure-Python Excel engine and compares to the Python models for all four scenarios, mandate pricing and three GCC locations: max relative error about 1e-15; no Excel error cells.

**Limitations.** Recalculation used the `formulas` library, not Excel or LibreOffice. The sensitivity grid is a first-order approximation.
