let
    Source = Csv.Document(File.Contents(FolderPath & "dim_region.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"region", type text},
        {"share", type number},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
