import pandas as pd

from src.api_tester.reports import summarize_report


def test_summarize_report_includes_performance_counts():
    report_df = pd.DataFrame(
        [
            {"overall_pass": True, "status_match": True, "response_match": True, "performance_match": True},
            {"overall_pass": False, "status_match": True, "response_match": False, "performance_match": False},
            {"overall_pass": False, "status_match": False, "response_match": True, "performance_match": True},
        ]
    )

    summary = summarize_report(report_df)

    assert summary["total"] == 3
    assert summary["performance_passed"] == 2
    assert summary["performance_failed"] == 1
