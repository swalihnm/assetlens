let
    Source = Csv.Document(File.Contents(FolderPath & "dim_business.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"business", type text},
        {"name", type text},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
