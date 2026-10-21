let
    Source = Csv.Document(File.Contents(FolderPath & "fact_top_down_bottom_up.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"business", type text},
        {"prior_year", type number},
        {"top_down", type number},
        {"bottom_up", type number},
        {"gap", type number},
        {"gap_pct", type number},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
