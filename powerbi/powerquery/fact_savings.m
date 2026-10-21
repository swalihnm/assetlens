let
    Source = Csv.Document(File.Contents(FolderPath & "fact_savings.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"initiative_id", type text},
        {"category", type text},
        {"target_savings_musd", type number},
        {"implementation_cost_musd", type number},
        {"headcount_impact", Int64.Type},
        {"owner", type text},
        {"confidence", type number},
        {"realised_to_date_musd", type number},
        {"depends_on", type text},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
