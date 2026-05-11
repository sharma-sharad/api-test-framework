from __future__ import annotations

import json
from typing import Any

from deepdiff import DeepDiff


def parse_response_body(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return text


def diff_json(old: Any, new: Any, ignore_order: bool = False) -> dict[str, Any]:
    diff = DeepDiff(
        old,
        new,
        ignore_order=ignore_order,
        verbose_level=2,
    )
    return json.loads(diff.to_json())


def compare_api_results(
    old_result: dict[str, Any],
    new_result: dict[str, Any],
    ignore_order: bool = False,
) -> dict[str, Any]:
    old_body = parse_response_body(old_result.get("response_text", ""))
    new_body = parse_response_body(new_result.get("response_text", ""))
    differences = diff_json(old_body, new_body, ignore_order=ignore_order)

    status_match = old_result.get("status_code") == new_result.get("status_code")
    response_match = not differences
    old_ms = float(old_result.get("elapsed_ms") or 0)
    new_ms = float(new_result.get("elapsed_ms") or 0)

    return {
        "status_match": status_match,
        "response_match": response_match,
        "performance_match": new_ms <= old_ms,
        "old_elapsed_ms": old_ms,
        "new_elapsed_ms": new_ms,
        "performance_delta_ms": new_ms - old_ms,
        "differences": differences,
        "overall_pass": status_match and response_match,
    }


def pretty_json(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, sort_keys=True, default=str)
