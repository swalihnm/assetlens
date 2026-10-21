let
    Source = Csv.Document(File.Contents(FolderPath & "fact_financials.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"fact_id", Int64.Type},
        {"ticker", type text},
        {"unit", type text},
        {"metric", type text},
        {"period_end", type datetime},
        {"value", type number},
        {"filed_date", type datetime},
        {"accession_no", type text},
        {"form_type", type text},
        {"method", type text}
    }, "en-US")
in
    Typed
