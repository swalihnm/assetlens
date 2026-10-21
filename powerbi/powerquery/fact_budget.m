let
    Source = Csv.Document(File.Contents(FolderPath & "fact_budget.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"period_end", type datetime},
        {"budget_revenue", type number},
        {"budget_pretax", type number},
        {"actual_revenue", type number},
        {"actual_pretax", type number},
        {"prior_year_revenue", type number},
        {"prior_year_pretax", type number},
        {"rev_variance", type number},
        {"rev_variance_pct", type number},
        {"pretax_variance", type number},
        {"pretax_variance_pct", type number},
        {"flag", type logical},
        {"owner_commentary", type text}
    }, "en-US")
in
    Typed
