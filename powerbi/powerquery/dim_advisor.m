let
    Source = Csv.Document(File.Contents(FolderPath & "dim_advisor.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"advisor_id", type text},
        {"hire_date", type datetime},
        {"left_date", type datetime},
        {"region", type text},
        {"book_initial_musd", type number},
        {"synthetic", type logical},
        {"cohort", Int64.Type}
    }, "en-US")
in
    Typed
