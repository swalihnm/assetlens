let
    Source = Csv.Document(File.Contents(FolderPath & "dim_company.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"ticker", type text},
        {"company", type text},
        {"unit_analysed", type text},
        {"asset_measure", type text},
        {"fiscal_year_end", type text}
    }, "en-US")
in
    Typed
