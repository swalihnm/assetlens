let
    Source = Csv.Document(File.Contents(FolderPath & "dim_metric.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"metric", type text}
    }, "en-US")
in
    Typed
