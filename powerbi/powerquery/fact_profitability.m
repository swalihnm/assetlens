let
    Source = Csv.Document(File.Contents(FolderPath & "fact_profitability.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"period_end", type text},
        {"method", type text},
        {"business", type text},
        {"allocated_musd", type number},
        {"net_revenues", type number},
        {"direct_comp", type number},
        {"direct_noncomp", type number},
        {"provision", type number},
        {"contribution_margin", type number},
        {"fully_allocated_pretax", type number},
        {"contribution_margin_pct", type number},
        {"fully_allocated_margin", type number},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
