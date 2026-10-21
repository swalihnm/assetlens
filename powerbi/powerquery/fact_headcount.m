let
    Source = Csv.Document(File.Contents(FolderPath & "fact_headcount.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"period_end", type text},
        {"business", type text},
        {"function", type text},
        {"region", type text},
        {"headcount", type number},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
