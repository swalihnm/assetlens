let
    Source = Csv.Document(File.Contents(FolderPath & "dim_function.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"pool", type text},
        {"name", type text},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
