let
    Source = Csv.Document(File.Contents(FolderPath & "mart_aum_decomposition.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"ticker", type text},
        {"start", type datetime},
        {"end", type datetime},
        {"quarters", Int64.Type},
        {"aum_begin", type number},
        {"aum_end", type number},
        {"net_flows", type number},
        {"market_fx_other", type number},
        {"organic_pct_of_begin", type number},
        {"market_pct_of_begin", type number}
    }, "en-US")
in
    Typed
