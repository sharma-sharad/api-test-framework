from __future__ import annotations

from io import BytesIO

import pandas as pd


def build_report_workbook(report_df: pd.DataFrame) -> BytesIO:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        report_df.to_excel(writer, sheet_name="api_validation_report", index=False)

        summary = pd.DataFrame(
            [
                {
                    "total_testcases": len(report_df),
                    "passed": int(report_df.get("overall_pass", pd.Series(dtype=bool)).fillna(False).sum()),
                    "failed": int((~report_df.get("overall_pass", pd.Series(dtype=bool)).fillna(False)).sum()),
                    "status_mismatches": int((~report_df.get("status_match", pd.Series(dtype=bool)).fillna(False)).sum()),
                    "response_mismatches": int((~report_df.get("response_match", pd.Series(dtype=bool)).fillna(False)).sum()),
                }
            ]
        )
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
        }

    overall = report_df.get("overall_pass", pd.Series([False] * len(report_df))).fillna(False)
    status = report_df.get("status_match", pd.Series([False] * len(report_df))).fillna(False)
    response = report_df.get("response_match", pd.Series([False] * len(report_df))).fillna(False)
    return {
        "total": len(report_df),
        "passed": int(overall.sum()),
        "failed": int((~overall).sum()),
        "status_mismatches": int((~status).sum()),
        "response_mismatches": int((~response).sum()),
    }
