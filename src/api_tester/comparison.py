from __future__ import annotations

import json
from typing import Any


def normalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [normalize_json(item) for item in value]
    return value


def parse_response_body(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return text


def diff_json(old: Any, new: Any, path: str = "$") -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []

    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(set(old) | set(new)):
            child_path = f"{path}.{key}"
            if key not in old:
                differences.append({"path": child_path, "type": "added", "old": None, "new": new[key]})
            elif key not in new:
                differences.append({"path": child_path, "type": "removed", "old": old[key], "new": None})
            else:
                differences.extend(diff_json(old[key], new[key], child_path))
        return differences

    if isinstance(old, list) and isinstance(new, list):
        max_len = max(len(old), len(new))
        for index in range(max_len):
            child_path = f"{path}[{index}]"
            if index >= len(old):
                differences.append({"path": child_path, "type": "added", "old": None, "new": new[index]})
            elif index >= len(new):
                differences.append({"path": child_path, "type": "removed", "old": old[index], "new": None})
            else:
                differences.extend(diff_json(old[index], new[index], child_path))
        return differences

    if old != new:
        differences.append({"path": path, "type": "changed", "old": old, "new": new})
    return differences


def compare_api_results(old_result: dict[str, Any], new_result: dict[str, Any]) -> dict[str, Any]:
    old_body = parse_response_body(old_result.get("response_text", ""))
    new_body = parse_response_body(new_result.get("response_text", ""))
    differences = diff_json(old_body, new_body)

    status_match = old_result.get("status_code") == new_result.get("status_code")
    response_match = normalize_json(old_body) == normalize_json(new_body)
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
