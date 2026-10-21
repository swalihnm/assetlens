let
    Source = Csv.Document(File.Contents(FolderPath & "dim_date.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"date", type datetime},
        {"year", Int64.Type},
        {"quarter_no", Int64.Type},
        {"month_no", Int64.Type},
        {"quarter_key", Int64.Type},
        {"quarter_label", type text},
        {"month_label", type text},
        {"quarter_end_date", type datetime},
        {"is_quarter_end", type logical},
        {"is_year_end", type logical}
    }, "en-US")
in
    Typed
