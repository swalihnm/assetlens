let
    Source = Csv.Document(File.Contents(FolderPath & "fact_advisor_monthly.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"period_end", type text},
        {"advisor_id", type text},
        {"revenue_musd", type number},
        {"nna_musd", type number},
        {"aum_musd", type number},
        {"clients", Int64.Type},
        {"tenure_years", type number},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
