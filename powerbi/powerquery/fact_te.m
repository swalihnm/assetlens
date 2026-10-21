let
    Source = Csv.Document(File.Contents(FolderPath & "fact_te.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"claim_id", Int64.Type},
        {"employee_id", Int64.Type},
        {"claim_date", type datetime},
        {"category", type text},
        {"amount_usd", type number},
        {"limit_usd", Int64.Type},
        {"has_receipt", type logical},
        {"violation_type", type text},
        {"is_violation", type logical},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
