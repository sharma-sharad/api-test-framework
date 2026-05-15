from __future__ import annotations

import json
import re
from typing import Any

from deepdiff import DeepDiff


PATH_TOKEN_PATTERN = re.compile(r"\['([^']+)'\]|\[(\d+)\]")


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


def format_path(path: str) -> str:
    if path == "root":
        return "response root"

    parts = []
    for field_name, list_index in PATH_TOKEN_PATTERN.findall(path):
        if field_name:
            parts.append(field_name)
        elif list_index:
            parts.append(f"item {int(list_index) + 1}")

    return " > ".join(parts) if parts else path


def format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, (int, float, bool)):
        return json.dumps(value)
    return json.dumps(value, sort_keys=True, default=str)


def summarize_differences(differences: dict[str, Any]) -> str:
    if not differences:
        return "No response differences found."

    lines: list[str] = []

    for path, values in differences.get("values_changed", {}).items():
        lines.append(
            "Changed "
            f"{format_path(path)} from {format_value(values.get('old_value'))} "
            f"to {format_value(values.get('new_value'))}."
        )

    for path, values in differences.get("type_changes", {}).items():
        lines.append(
            "Changed type for "
            f"{format_path(path)} from {values.get('old_type', 'old type')} "
            f"to {values.get('new_type', 'new type')}. "
            f"Old value: {format_value(values.get('old_value'))}; "
            f"new value: {format_value(values.get('new_value'))}."
        )

    for path, value in differences.get("dictionary_item_added", {}).items():
        lines.append(f"Added field {format_path(path)} with value {format_value(value)}.")

    for path, value in differences.get("dictionary_item_removed", {}).items():
        lines.append(f"Removed field {format_path(path)}. Old value was {format_value(value)}.")

    for path, value in differences.get("iterable_item_added", {}).items():
        lines.append(f"Added list value at {format_path(path)}: {format_value(value)}.")

    for path, value in differences.get("iterable_item_removed", {}).items():
        lines.append(f"Removed list value at {format_path(path)}. Old value was {format_value(value)}.")

    if lines:
        return "\n".join(f"{index}. {line}" for index, line in enumerate(lines, start=1))

    return json.dumps(differences, indent=2, sort_keys=True, default=str)


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
        "differences_summary": summarize_differences(differences),
        "overall_pass": status_match and response_match,
    }


def pretty_json(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, sort_keys=True, default=str)
