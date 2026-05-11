from src.api_tester import templates


def test_template_dataframe_does_not_require_id_column(monkeypatch):
    monkeypatch.setitem(
        templates.SHEET_DYNAMIC_COLUMNS,
        "claims_adjuster",
        ["claimRequestNumber", "requestedBy", "claimStatus"],
    )

    df = templates.template_dataframe("claims_adjuster", sample_rows=2)

    assert list(df.columns) == [
        "TestcaseNumber",
        "oldendpoint",
        "newendpoint",
        "method",
        "claimRequestNumber",
        "requestedBy",
        "claimStatus",
    ]
    assert df.loc[0, "claimRequestNumber"] == "claimRequestNumber_1"
    assert df.loc[1, "requestedBy"] == "requestedBy_2"
