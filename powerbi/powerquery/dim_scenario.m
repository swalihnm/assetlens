let
    Source = Csv.Document(File.Contents(FolderPath & "dim_scenario.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"scenario", type text},
        {"sort", Int64.Type}
    }, "en-US")
in
    Typed
