let
    Source = Csv.Document(File.Contents(FolderPath & "comparability_flags.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"ticker", type text},
        {"topic", type text},
        {"note", type text}
    }, "en-US")
in
    Typed
