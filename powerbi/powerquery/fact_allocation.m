let
    Source = Csv.Document(File.Contents(FolderPath & "fact_allocation.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"period_end", type text},
        {"method", type text},
        {"pool", type text},
        {"business", type text},
        {"allocated_musd", type number},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
