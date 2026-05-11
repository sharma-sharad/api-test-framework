from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests

from .comparison import compare_api_results
from .logging_config import audit_event, setup_logging
from .ssl_config import build_verify_option
from .templates import COMMON_COLUMNS


LOGGER = setup_logging()


@dataclass(frozen=True)
class ExecutionConfig:
    session_id: str
    timeout: int = 60
    max_workers: int = 5
    ignore_order: bool = False
    verify_ssl: bool = True
    ca_bundle_path: str | None = None


def row_to_request_body(row: pd.Series) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for column, value in row.items():
        if column in COMMON_COLUMNS or pd.isna(value):
            continue
        body[column] = value.item() if hasattr(value, "item") else value
    return body


def build_headers(session_id: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "IDS-SESSION-ID": session_id,
    }


def call_api(
    endpoint: str,
    method: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: int,
    verify: bool | str = True,
) -> dict[str, Any]:
    start = time.perf_counter()
    error = None
    status_code = None
    response_text = ""

    try:
        response = requests.request(
            method.upper(),
            endpoint,
            headers=headers,
            json=body if method.upper() not in {"GET", "DELETE"} else None,
            params=body if method.upper() in {"GET", "DELETE"} else None,
            timeout=timeout,
            verify=verify,
        )
        status_code = response.status_code
        response_text = response.text
    except requests.RequestException as exc:
        error = str(exc)
        LOGGER.exception("API call failed: method=%s endpoint=%s", method, endpoint)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    return {
        "endpoint": endpoint,
        "method": method.upper(),
        "status_code": status_code,
        "response_text": response_text,
        "elapsed_ms": elapsed_ms,
        "error": error,
    }


def execute_row(sheet_name: str, row: pd.Series, config: ExecutionConfig) -> dict[str, Any]:
    testcase_number = str(row["TestcaseNumber"])
    method = str(row["method"]).upper()
    body = row_to_request_body(row)
    headers = build_headers(config.session_id)
    verify = build_verify_option(config.verify_ssl, config.ca_bundle_path)

    LOGGER.info("Executing testcase=%s sheet=%s method=%s", testcase_number, sheet_name, method)
    audit_event(
        "testcase_started",
        {"sheet": sheet_name, "testcase_number": testcase_number, "method": method},
    )

    old_result = call_api(str(row["oldendpoint"]), method, headers, body, config.timeout, verify)
    new_result = call_api(str(row["newendpoint"]), method, headers, body, config.timeout, verify)
    comparison = compare_api_results(
        old_result,
        new_result,
        ignore_order=config.ignore_order,
    )

    audit_event(
        "testcase_completed",
        {
            "sheet": sheet_name,
            "testcase_number": testcase_number,
            "status_match": comparison["status_match"],
            "response_match": comparison["response_match"],
            "overall_pass": comparison["overall_pass"],
        },
    )

    return {
        "SheetName": sheet_name,
        "TestcaseNumber": testcase_number,
        "oldendpoint": row["oldendpoint"],
        "newendpoint": row["newendpoint"],
        "method": method,
        "request_headers": json.dumps(headers, indent=2),
        "request_body": json.dumps(body, indent=2, default=str),
        "old_status_code": old_result["status_code"],
        "new_status_code": new_result["status_code"],
        "old_response": old_result["response_text"],
        "new_response": new_result["response_text"],
        "old_elapsed_ms": old_result["elapsed_ms"],
        "new_elapsed_ms": new_result["elapsed_ms"],
        "performance_delta_ms": comparison["performance_delta_ms"],
        "status_match": comparison["status_match"],
        "response_match": comparison["response_match"],
        "performance_match": comparison["performance_match"],
        "overall_pass": comparison["overall_pass"],
        "ignore_order": config.ignore_order,
        "verify_ssl": config.verify_ssl,
        "ca_bundle_path": config.ca_bundle_path or "",
        "differences": json.dumps(comparison["differences"], indent=2, default=str),
        "old_error": old_result["error"],
        "new_error": new_result["error"],
    }


def validate_dataframe(df: pd.DataFrame) -> None:
    missing = [column for column in COMMON_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def execute_sheets(
    sheets: dict[str, pd.DataFrame],
    config: ExecutionConfig,
) -> pd.DataFrame:
    jobs = []
    results = []

    for sheet_name, df in sheets.items():
        validate_dataframe(df)
        for _, row in df.iterrows():
            jobs.append((sheet_name, row))

    LOGGER.info("Starting execution for %s testcases with max_workers=%s", len(jobs), config.max_workers)
    audit_event("execution_started", {"testcase_count": len(jobs), "max_workers": config.max_workers})

    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        future_map = {
            executor.submit(execute_row, sheet_name, row, config): (sheet_name, row["TestcaseNumber"])
            for sheet_name, row in jobs
        }
        for future in as_completed(future_map):
            sheet_name, testcase_number = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                LOGGER.exception("Testcase crashed: sheet=%s testcase=%s", sheet_name, testcase_number)
                results.append(
                    {
                        "SheetName": sheet_name,
                        "TestcaseNumber": testcase_number,
                        "overall_pass": False,
                        "old_error": str(exc),
                        "new_error": str(exc),
                    }
                )

    report_df = pd.DataFrame(results)
    report_df = report_df.sort_values(["SheetName", "TestcaseNumber"], ignore_index=True)
    audit_event("execution_completed", {"testcase_count": len(report_df)})
    return report_df
