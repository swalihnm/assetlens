let
    Source = Csv.Document(File.Contents(FolderPath & "dim_initiative.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"initiative_id", type text},
        {"category", type text},
        {"owner", type text},
        {"depends_on", type text},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
