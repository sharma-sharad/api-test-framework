from __future__ import annotations

from io import BytesIO

import pandas as pd


COMMON_COLUMNS = ["TestcaseNumber", "oldendpoint", "newendpoint", "method"]

SHEET_DYNAMIC_COLUMNS: dict[str, list[str]] = {
    "claims_adjuster": ["id", "username", "adjusterName", "region", "status"],
    "claims_details": ["id", "claimNumber", "policyNumber", "lossDate", "claimType"],
    "claims_search": ["id", "username", "searchText", "fromDate", "toDate"],
    "claims_consumers": ["id", "username", "consumerId", "email", "phoneNumber"],
}

SAMPLE_VALUES: dict[str, dict[str, object]] = {
    "claims_adjuster": {
        "id": 1001,
        "username": "adjuster.user",
        "adjusterName": "Jane Adjuster",
        "region": "East",
        "status": "ACTIVE",
    },
    "claims_details": {
        "id": 2001,
        "claimNumber": "CLM-10001",
        "policyNumber": "POL-90001",
        "lossDate": "2026-05-01",
        "claimType": "AUTO",
    },
    "claims_search": {
        "id": 3001,
        "username": "claims.user",
        "searchText": "open claims",
        "fromDate": "2026-01-01",
        "toDate": "2026-05-11",
    },
    "claims_consumers": {
        "id": 4001,
        "username": "consumer.user",
        "consumerId": "C-10001",
        "email": "consumer@example.com",
        "phoneNumber": "5550100",
    },
}


def supported_sheets() -> list[str]:
    return list(SHEET_DYNAMIC_COLUMNS)


def template_dataframe(sheet_name: str, sample_rows: int = 3) -> pd.DataFrame:
    columns = COMMON_COLUMNS + SHEET_DYNAMIC_COLUMNS[sheet_name]
    rows = []
    for index in range(1, sample_rows + 1):
        row = {
            "TestcaseNumber": f"TC{index}",
            "oldendpoint": "https://old-api.example.com/resource",
            "newendpoint": "https://new-api.example.com/resource",
            "method": "POST",
        }
        row.update(SAMPLE_VALUES[sheet_name])
        row["id"] = SAMPLE_VALUES[sheet_name]["id"] + index - 1
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def build_template_workbook(sheet_names: list[str]) -> BytesIO:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name in sheet_names:
            template_dataframe(sheet_name).to_excel(
                writer, sheet_name=sheet_name, index=False
            )
    buffer.seek(0)
    return buffer


def read_selected_sheets(uploaded_file, sheet_names: list[str]) -> dict[str, pd.DataFrame]:
    workbook = pd.ExcelFile(uploaded_file)
    available = set(workbook.sheet_names)
    missing = [sheet for sheet in sheet_names if sheet not in available]
    if missing:
        raise ValueError(f"Uploaded file is missing sheets: {', '.join(missing)}")
    return {sheet: pd.read_excel(workbook, sheet_name=sheet) for sheet in sheet_names}
