# M16 Board pack

**Method.** python-pptx deck built from warehouse queries (every number comes from a single `numbers()` function): executive summary, competitive position, outlook and risk, profitability and pricing, growth and initiatives, appendix with methodology and the disclaimer. A renderer draws each slide from the .pptx to PDF and PNG and flags text overflow. Charts follow a validated colour palette with fixed colour per company and de-collided labels.

**Outputs.** `outputs/deck/AssetLens_Board_Pack.pptx` and `.pdf`.

**Results and validation.** Test re-derives the headline numbers from the warehouse and checks they appear on the slides; PDF render test checks 6 pages and no overflow.

**Limitations.** The PDF is drawn from the pptx contents (not PowerPoint's own renderer), so spacing can differ slightly.
