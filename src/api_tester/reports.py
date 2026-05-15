from __future__ import annotations

from io import BytesIO

import pandas as pd


def bool_series(report_df: pd.DataFrame, column: str) -> pd.Series:
    return report_df.get(column, pd.Series([False] * len(report_df))).fillna(False).astype(bool)


def build_report_workbook(report_df: pd.DataFrame) -> BytesIO:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        report_df.to_excel(writer, sheet_name="api_validation_report", index=False)
        summary = pd.DataFrame([summarize_report(report_df)]).rename(columns={"total": "total_testcases"})
        summary.to_excel(writer, sheet_name="summary", index=False)
    buffer.seek(0)
    return buffer


def summarize_report(report_df: pd.DataFrame) -> dict[str, int]:
    if report_df.empty:
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "status_mismatches": 0,
            "response_mismatches": 0,
            "performance_passed": 0,
            "performance_failed": 0,
        }

    overall = bool_series(report_df, "overall_pass")
    status = bool_series(report_df, "status_match")
    response = bool_series(report_df, "response_match")
    performance = bool_series(report_df, "performance_match")
    return {
        "total": len(report_df),
        "passed": int(overall.sum()),
        "failed": int((~overall).sum()),
        "status_mismatches": int((~status).sum()),
        "response_mismatches": int((~response).sum()),
        "performance_passed": int(performance.sum()),
        "performance_failed": int((~performance).sum()),
    }
