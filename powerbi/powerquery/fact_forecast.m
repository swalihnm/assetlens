let
    Source = Csv.Document(File.Contents(FolderPath & "fact_forecast.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"scenario", type text},
        {"period_end", type datetime},
        {"t", Int64.Type},
        {"aus_alternatives", type number},
        {"aus_equity", type number},
        {"aus_fixed_income", type number},
        {"aus_liquidity", type number},
        {"aus_total", type number},
        {"net_flows", type number},
        {"mgmt_fees", type number},
        {"incentive_fees", type number},
        {"private_banking_lending", type number},
        {"investments", type number},
        {"net_revenues", type number},
        {"comp", type number},
        {"noncomp", type number},
        {"provision", type number},
        {"pretax", type number},
        {"pretax_margin", type number},
        {"core_pretax_margin", type number},
        {"fee_yield_bps", type number},
        {"comp_ratio", type number},
        {"yield_alternatives_bps", type number},
        {"yield_equity_bps", type number},
        {"yield_fixed_income_bps", type number},
        {"yield_liquidity_bps", type number},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
