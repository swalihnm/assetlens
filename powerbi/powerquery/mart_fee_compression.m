let
    Source = Csv.Document(File.Contents(FolderPath & "mart_fee_compression.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"ticker", type text},
        {"start", type datetime},
        {"end", type datetime},
        {"n", Int64.Type},
        {"slope_bps_per_year", type number},
        {"ci_low", type number},
        {"ci_high", type number},
        {"pct_per_year", type number},
        {"significant", type logical}
    }, "en-US")
in
    Typed
