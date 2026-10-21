let
    Source = Csv.Document(File.Contents(FolderPath & "dim_vendor.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"vendor_id", type text},
        {"vendor_name", type text},
        {"category", type text},
        {"tier", type text},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
