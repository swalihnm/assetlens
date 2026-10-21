# Data dictionary (auto-generated from DuckDB)

Tables flagged **synthetic** carry a `synthetic = true` column.

## comparability_flags
21 rows

| Column | Type |
|---|---|
| ticker | VARCHAR |
| topic | VARCHAR |
| note | VARCHAR |

## dim_advisor - **synthetic**
800 rows

| Column | Type |
|---|---|
| advisor_id | VARCHAR |
| hire_date | TIMESTAMP_NS |
| left_date | TIMESTAMP_NS |
| region | VARCHAR |
| book_initial_musd | DOUBLE |
| synthetic | BOOLEAN |
| cohort | INTEGER |

## dim_business - **synthetic**
6 rows

| Column | Type |
|---|---|
| business | VARCHAR |
| name | VARCHAR |
| synthetic | BOOLEAN |

## dim_function - **synthetic**
5 rows

| Column | Type |
|---|---|
| pool | VARCHAR |
| name | VARCHAR |
| synthetic | BOOLEAN |

## dim_region - **synthetic**
4 rows

| Column | Type |
|---|---|
| region | VARCHAR |
| share | DOUBLE |
| synthetic | BOOLEAN |

## dim_support_usage - **synthetic**
25 rows

| Column | Type |
|---|---|
| provider | VARCHAR |
| user | VARCHAR |
| share | DOUBLE |
| synthetic | BOOLEAN |

## dim_vendor - **synthetic**
1,200 rows

| Column | Type |
|---|---|
| vendor_id | VARCHAR |
| vendor_name | VARCHAR |
| category | VARCHAR |
| tier | VARCHAR |
| weight | DOUBLE |
| synthetic | BOOLEAN |

## fact_advisor_monthly - **synthetic**
10,611 rows

| Column | Type |
|---|---|
| period_end | VARCHAR |
| advisor_id | VARCHAR |
| revenue_musd | DOUBLE |
| nna_musd | DOUBLE |
| aum_musd | DOUBLE |
| clients | BIGINT |
| tenure_years | DOUBLE |
| synthetic | BOOLEAN |

## fact_allocation - **synthetic**
2,700 rows

| Column | Type |
|---|---|
| period_end | VARCHAR |
| method | VARCHAR |
| pool | VARCHAR |
| business | VARCHAR |
| allocated_musd | DOUBLE |
| synthetic | BOOLEAN |

## fact_business_pnl - **synthetic**
108 rows

| Column | Type |
|---|---|
| mgmt_fees | DOUBLE |
| incentive_fees | DOUBLE |
| pbl | DOUBLE |
| investments | DOUBLE |
| net_revenues | DOUBLE |
| direct_comp | DOUBLE |
| direct_noncomp | DOUBLE |
| provision | DOUBLE |
| contribution_margin | DOUBLE |
| period_end | VARCHAR |
| business | VARCHAR |
| synthetic | BOOLEAN |

## fact_comp - **synthetic**
3,066 rows

| Column | Type |
|---|---|
| advisor_id | VARCHAR |
| year | BIGINT |
| revenue | DOUBLE |
| nna | DOUBLE |
| tenure | DOUBLE |
| region | VARCHAR |
| comp_musd | DOUBLE |
| synthetic | BOOLEAN |

## fact_cost_pools - **synthetic**
90 rows

| Column | Type |
|---|---|
| period_end | VARCHAR |
| pool | VARCHAR |
| cost | DOUBLE |
| synthetic | BOOLEAN |

## fact_drivers - **synthetic**
540 rows

| Column | Type |
|---|---|
| period_end | VARCHAR |
| pool | VARCHAR |
| business | VARCHAR |
| driver | VARCHAR |
| quantity | DOUBLE |
| synthetic | BOOLEAN |

## fact_financials
2,475 rows

| Column | Type |
|---|---|
| fact_id | BIGINT |
| ticker | VARCHAR |
| unit | VARCHAR |
| metric | VARCHAR |
| period_end | VARCHAR |
| period_type | VARCHAR |
| value | DOUBLE |
| currency | VARCHAR |
| scale | VARCHAR |

## fact_forecast - **synthetic**
32 rows

| Column | Type |
|---|---|
| scenario | VARCHAR |
| period_end | TIMESTAMP |
| t | BIGINT |
| aus_alternatives | DOUBLE |
| aus_equity | DOUBLE |
| aus_fixed_income | DOUBLE |
| aus_liquidity | DOUBLE |
| aus_total | DOUBLE |
| net_flows | DOUBLE |
| mgmt_fees | DOUBLE |
| incentive_fees | DOUBLE |
| private_banking_lending | DOUBLE |
| investments | DOUBLE |
| net_revenues | DOUBLE |
| comp | DOUBLE |
| noncomp | DOUBLE |
| provision | DOUBLE |
| pretax | DOUBLE |
| pretax_margin | DOUBLE |
| core_pretax_margin | DOUBLE |
| fee_yield_bps | DOUBLE |
| comp_ratio | DOUBLE |
| yield_alternatives_bps | DOUBLE |
| yield_equity_bps | DOUBLE |
| yield_fixed_income_bps | DOUBLE |
| yield_liquidity_bps | DOUBLE |
| synthetic | BOOLEAN |

## fact_gl - **synthetic**
2,599,992 rows

| Column | Type |
|---|---|
| posting_date | TIMESTAMP |
| cost_center | VARCHAR |
| owner | VARCHAR |
| region | VARCHAR |
| category | VARCHAR |
| vendor_id | VARCHAR |
| is_comp | BOOLEAN |
| period_end | VARCHAR |
| amount_musd | DOUBLE |
| txn_id | BIGINT |
| synthetic | BOOLEAN |

## fact_headcount - **synthetic**
792 rows

| Column | Type |
|---|---|
| period_end | VARCHAR |
| business | VARCHAR |
| function | VARCHAR |
| region | VARCHAR |
| headcount | DOUBLE |
| synthetic | BOOLEAN |

## fact_market
319 rows

| Column | Type |
|---|---|
| period_end | TIMESTAMP |
| SP500_ret | DOUBLE |
| BAMLCC0A0CMTRIV_ret | DOUBLE |
| BAMLHYH0A0HYM2TRIV_ret | DOUBLE |
| DGS10_avg | DOUBLE |
| DGS2_avg | DOUBLE |
| DFF_avg | DOUBLE |
| DEXUSEU_avg | DOUBLE |
| CPIAUCSL_avg | DOUBLE |

## fact_pipeline - **synthetic**
18 rows

| Column | Type |
|---|---|
| period_end | TIMESTAMP |
| leads | BIGINT |
| meetings | BIGINT |
| proposals | BIGINT |
| wins | BIGINT |
| nna_musd | DOUBLE |
| lead_to_meeting | DOUBLE |
| meeting_to_proposal | DOUBLE |
| proposal_to_win | DOUBLE |
| synthetic | BOOLEAN |

## fact_provenance
2,475 rows

| Column | Type |
|---|---|
| fact_id | BIGINT |
| source_url | VARCHAR |
| accession_no | VARCHAR |
| form_type | VARCHAR |
| filed_date | VARCHAR |
| document | VARCHAR |
| locator | VARCHAR |
| raw_text | VARCHAR |
| method | VARCHAR |
| confidence | DOUBLE |
| reviewed | BOOLEAN |
| retrieved_at | VARCHAR |

## fact_savings - **synthetic**
40 rows

| Column | Type |
|---|---|
| initiative_id | VARCHAR |
| category | VARCHAR |
| target_savings_musd | DOUBLE |
| implementation_cost_musd | DOUBLE |
| headcount_impact | BIGINT |
| owner | VARCHAR |
| confidence | DOUBLE |
| realised_to_date_musd | DOUBLE |
| depends_on | VARCHAR |
| synthetic | BOOLEAN |

## fact_te - **synthetic**
201,179 rows

| Column | Type |
|---|---|
| claim_id | BIGINT |
| employee_id | BIGINT |
| claim_date | TIMESTAMP |
| category | VARCHAR |
| amount_usd | DOUBLE |
| limit_usd | BIGINT |
| has_receipt | BOOLEAN |
| violation_type | VARCHAR |
| is_violation | BOOLEAN |
| synthetic | BOOLEAN |

## llm_calls
438 rows

| Column | Type |
|---|---|
| ts | TIMESTAMP |
| provider | VARCHAR |
| model | VARCHAR |
| latency_s | DOUBLE |
| input_tokens | BIGINT |
| output_tokens | BIGINT |
| cost_usd | DOUBLE |

## mart_allocation_rank_sensitivity
30 rows

| Column | Type |
|---|---|
| method | VARCHAR |
| business | VARCHAR |
| revenue | DOUBLE |
| pretax | DOUBLE |
| margin | DOUBLE |
| rank | BIGINT |

## mart_aum_decomposition
7 rows

| Column | Type |
|---|---|
| ticker | VARCHAR |
| start | DATE |
| end | DATE |
| quarters | BIGINT |
| aum_begin | DOUBLE |
| aum_end | DOUBLE |
| net_flows | DOUBLE |
| market_fx_other | DOUBLE |
| organic_pct_of_begin | DOUBLE |
| market_pct_of_begin | DOUBLE |

## mart_backtest_errors
130 rows

| Column | Type |
|---|---|
| origin | TIMESTAMP |
| horizon | BIGINT |
| model | VARCHAR |
| actual | DOUBLE |
| forecast | DOUBLE |
| error | DOUBLE |
| ape | DOUBLE |

## mart_backtest_summary
20 rows

| Column | Type |
|---|---|
| model | VARCHAR |
| horizon | BIGINT |
| mape | DOUBLE |
| bias | DOUBLE |
| n | BIGINT |

## mart_budget_variance
4 rows

| Column | Type |
|---|---|
| period_end | TIMESTAMP |
| budget_revenue | DOUBLE |
| budget_pretax | DOUBLE |
| actual_revenue | DOUBLE |
| actual_pretax | DOUBLE |
| prior_year_revenue | DOUBLE |
| prior_year_pretax | DOUBLE |
| rev_variance | DOUBLE |
| rev_variance_pct | DOUBLE |
| pretax_variance | DOUBLE |
| pretax_variance_pct | DOUBLE |
| flag | BOOLEAN |
| owner_commentary | VARCHAR |

## mart_cohort_ramp - **synthetic**
157 rows

| Column | Type |
|---|---|
| cohort | INTEGER |
| tenure_bucket | DOUBLE |
| revenue_per_advisor_q | DOUBLE |
| advisors | BIGINT |
| synthetic | BOOLEAN |

## mart_fee_compression
7 rows

| Column | Type |
|---|---|
| ticker | VARCHAR |
| start | DATE |
| end | DATE |
| n | BIGINT |
| slope_bps_per_year | DOUBLE |
| ci_low | DOUBLE |
| ci_high | DOUBLE |
| pct_per_year | DOUBLE |
| significant | BOOLEAN |

## mart_market_beta_rolling
114 rows

| Column | Type |
|---|---|
| ticker | VARCHAR |
| period_end | TIMESTAMP |
| beta_equity | DOUBLE |
| beta_bond | DOUBLE |

## mart_market_sensitivity
7 rows

| Column | Type |
|---|---|
| ticker | VARCHAR |
| n | BIGINT |
| beta_equity | DOUBLE |
| eq_ci_low | DOUBLE |
| eq_ci_high | DOUBLE |
| beta_bond | DOUBLE |
| bd_ci_low | DOUBLE |
| bd_ci_high | DOUBLE |
| alpha_q | DOUBLE |
| r2 | DOUBLE |
| dw | DOUBLE |
| note | VARCHAR |

## mart_montecarlo_fan
24 rows

| Column | Type |
|---|---|
| t | BIGINT |
| metric | VARCHAR |
| p10 | DOUBLE |
| p50 | DOUBLE |
| p90 | DOUBLE |

## mart_montecarlo_prob
1 rows

| Column | Type |
|---|---|
| margin_below_threshold_q8 | DOUBLE |
| margin_below_threshold_any | DOUBLE |
| threshold | DOUBLE |
| n | BIGINT |
| hist_quarters | BIGINT |
| pretax_8q_p10 | DOUBLE |
| pretax_8q_p50 | DOUBLE |
| pretax_8q_p90 | DOUBLE |

## mart_nna_forecast - **synthetic**
4 rows

| Column | Type |
|---|---|
| quarter | VARCHAR |
| forecast | DOUBLE |
| p10 | DOUBLE |
| p90 | DOUBLE |
| synthetic | BOOLEAN |

## mart_peer_benchmark
201 rows

| Column | Type |
|---|---|
| period_end | TIMESTAMP |
| ticker | VARCHAR |
| aum_end | DOUBLE |
| aum_begin | DOUBLE |
| aum_avg | DOUBLE |
| aum_avg_method | VARCHAR |
| net_flows | DOUBLE |
| market_other | DOUBLE |
| fees | DOUBLE |
| net_revenues | DOUBLE |
| op_income | DOUBLE |
| opex | DOUBLE |
| comp | DOUBLE |
| op_income_adj | DOUBLE |
| fee_yield_bps | DOUBLE |
| organic_growth_ann | DOUBLE |
| market_impact_pct | DOUBLE |
| op_margin | DOUBLE |
| comp_ratio | DOUBLE |
| efficiency_ratio | DOUBLE |
| fee_share_of_revenue | DOUBLE |
| fee_yield_t4q_bps | DOUBLE |
| organic_growth_t4q | DOUBLE |
| op_margin_t4q | DOUBLE |
| comp_ratio_t4q | DOUBLE |
| operating_leverage_yoy | DOUBLE |
| revenue_yoy | DOUBLE |
| aum_yoy | DOUBLE |
| z_fee_yield_t4q_bps | DOUBLE |
| z_organic_growth_t4q | DOUBLE |
| z_op_margin_t4q | DOUBLE |

## mart_profitability_by_business - **synthetic**
540 rows

| Column | Type |
|---|---|
| period_end | VARCHAR |
| method | VARCHAR |
| business | VARCHAR |
| allocated_musd | DOUBLE |
| net_revenues | DOUBLE |
| direct_comp | DOUBLE |
| direct_noncomp | DOUBLE |
| provision | DOUBLE |
| contribution_margin | DOUBLE |
| fully_allocated_pretax | DOUBLE |
| contribution_margin_pct | DOUBLE |
| fully_allocated_margin | DOUBLE |
| synthetic | BOOLEAN |

## mart_sales_productivity - **synthetic**
72 rows

| Column | Type |
|---|---|
| period_end | TIMESTAMP |
| region | VARCHAR |
| advisors | BIGINT |
| revenue | DOUBLE |
| nna | DOUBLE |
| aum | DOUBLE |
| clients | BIGINT |
| quota_attainment | DOUBLE |
| revenue_per_advisor | DOUBLE |
| aum_per_advisor | DOUBLE |
| wallet_proxy_revenue_bps_of_aum | DOUBLE |
| synthetic | BOOLEAN |

## mart_top_down_vs_bottom_up - **synthetic**
6 rows

| Column | Type |
|---|---|
| business | VARCHAR |
| prior_year | DOUBLE |
| top_down | DOUBLE |
| bottom_up | DOUBLE |
| gap | DOUBLE |
| gap_pct | DOUBLE |
| synthetic | BOOLEAN |

## restatement_log
262 rows

| Column | Type |
|---|---|
| ticker | VARCHAR |
| unit | VARCHAR |
| metric | VARCHAR |
| period_end | VARCHAR |
| period_type | VARCHAR |
| value | DOUBLE |
| currency | VARCHAR |
| scale | VARCHAR |
| perimeter | VARCHAR |
| source_url | VARCHAR |
| accession_no | VARCHAR |
| form_type | VARCHAR |
| filed_date | VARCHAR |
| document | VARCHAR |
| locator | VARCHAR |
| raw_text | VARCHAR |
| method | VARCHAR |
| confidence | DOUBLE |
| reviewed | BOOLEAN |
| original_value | DOUBLE |
