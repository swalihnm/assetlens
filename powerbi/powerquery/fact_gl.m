let
    Source = Parquet.Document(File.Contents(FolderPath & "fact_gl.parquet"), [Compressed = true]),
    Typed = Table.TransformColumnTypes(Source, {
        {"txn_id", Int64.Type},
        {"posting_date", type datetime},
        {"period_end", type text},
        {"cost_center", type text},
        {"owner", type text},
        {"region", type text},
        {"category", type text},
        {"vendor_id", type text},
        {"is_comp", type logical},
        {"amount_musd", type number},
        {"synthetic", type logical}
    }, "en-US")
in
    Typed
