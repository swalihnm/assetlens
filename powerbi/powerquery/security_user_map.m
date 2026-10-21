let
    Source = Csv.Document(File.Contents(FolderPath & "security_user_map.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"user_principal_name", type text},
        {"business", type text},
        {"region", type text}
    }, "en-US")
in
    Typed
