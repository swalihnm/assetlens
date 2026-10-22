# M15 Power BI assets and Streamlit app

**Method.** Parquet/CSV star schema (27 tables) with Power Query scripts per table, about 55 DAX measures (peer benchmarks, T4Q, YoY/QoQ, forecast, budget variance, profitability by method, sales, expense), a role-playing date dimension, row-level security design (business head and regional CFO via a user-mapping table and USERPRINCIPALNAME), page wireframes for 8 pages, and 11 spot-check values from the warehouse. A Streamlit app mirrors the 8 pages.

**Outputs.** `outputs/powerbi/`, `powerbi/measures.dax`, `powerbi/model.md`, `powerbi/powerquery/*.m`, `app/streamlit_app.py`.

**Results and validation.** Streamlit smoke test renders every page without error. Spot-check expectations are generated from the warehouse.

**Limitations.** The .pbix itself is not included (needs Power BI Desktop) and the DAX has not been executed in Power BI.
