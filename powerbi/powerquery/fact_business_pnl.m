let
    Source = Csv.Document(File.Contents(FolderPath & "fact_business_pnl.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"mgmt_fees", type number},
        {"incentive_fees", type number},
        {"pbl", type number},
        {"investments", type number},
        {"net_revenues", type number},
        {"direct_comp", type number},
        {"direct_noncomp", type number},
        {"provision", type number},
        {"contribution_margin", type number},
        {"period_end", type text},
        {"business", type text},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
