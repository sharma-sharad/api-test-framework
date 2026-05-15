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
            parts.append(f"record {int(list_index) + 1}")

    return " > ".join(parts) if parts else path


def path_tokens(path: str) -> list[str]:
    tokens = []
    for field_name, list_index in PATH_TOKEN_PATTERN.findall(path):
        if field_name:
            tokens.append(field_name)
        elif list_index:
            tokens.append(f"record {int(list_index) + 1}")
    return tokens


def describe_change_location(path: str) -> tuple[str, str | None]:
    tokens = path_tokens(path)
    if not tokens:
        return "response root", None

    field_name = tokens[-1]
    parent_tokens = tokens[:-1]
    if not parent_tokens:
        return "response root", field_name

    return " > ".join(parent_tokens), field_name


def describe_container_location(path: str) -> str:
    tokens = path_tokens(path)
    if not tokens:
        return "response root"
    return " > ".join(tokens)


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
        parent, field_name = describe_change_location(path)
        if field_name:
            lines.append(
                f"For {parent}, field {field_name} changed from "
                f"{format_value(values.get('old_value'))} in old API to "
                f"{format_value(values.get('new_value'))} in new API."
            )
            continue
        lines.append(
            f"Response changed from {format_value(values.get('old_value'))} "
            f"in old API to {format_value(values.get('new_value'))} in new API."
        )

    for path, values in differences.get("type_changes", {}).items():
        parent, field_name = describe_change_location(path)
        field_text = f"field {field_name}" if field_name else "response"
        lines.append(
            f"For {parent}, {field_text} changed type. Old API value was "
            f"{format_value(values.get('old_value'))}; new API value is "
            f"{format_value(values.get('new_value'))}."
        )

    for path, value in differences.get("dictionary_item_added", {}).items():
        parent, field_name = describe_change_location(path)
        if field_name:
            lines.append(
                f"In new API, field {field_name} was added under {parent} "
                f"with value {format_value(value)}."
            )
        else:
            lines.append(f"In new API, response value was added: {format_value(value)}.")

    for path, value in differences.get("dictionary_item_removed", {}).items():
        parent, field_name = describe_change_location(path)
        if field_name:
            lines.append(
                f"Field {field_name} existed under {parent} in old API but is missing "
                f"in new API. Old API value was {format_value(value)}."
            )
        else:
            lines.append(f"Old API response value is missing in new API: {format_value(value)}.")

    for path, value in differences.get("iterable_item_added", {}).items():
        lines.append(
            f"New API added {describe_container_location(path)} with value {format_value(value)}."
        )

    for path, value in differences.get("iterable_item_removed", {}).items():
        lines.append(
            f"Old API had {describe_container_location(path)}, but it is missing in new API. "
            f"Old API value was {format_value(value)}."
        )

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
