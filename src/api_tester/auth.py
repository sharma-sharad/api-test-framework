from __future__ import annotations

from typing import Any

import requests

from .logging_config import audit_event, setup_logging
from .ssl_config import build_verify_option


LOGGER = setup_logging()


def extract_session_id(response_json: dict[str, Any]) -> str:
    candidates = [
        ("sessionID",),
        ("sessionId",),
        ("session_id",),
        ("data", "sessionID"),
        ("data", "sessionId"),
        ("data", "session_id"),
    ]
    for path in candidates:
        value: Any = response_json
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value:
            return str(value)
    raise ValueError("Authentication response did not contain sessionID")


def authenticate(
    auth_url: str,
    username: str,
    password: str,
    timeout: int = 30,
    verify_ssl: bool = True,
    ca_bundle_path: str | None = None,
) -> str:
    LOGGER.info("Starting authentication request for user=%s", username)
    audit_event(
        "authentication_started",
        {
            "auth_url": auth_url,
            "username": username,
            "verify_ssl": verify_ssl,
            "ca_bundle_path_provided": bool(ca_bundle_path),
        },
    )

    response = requests.post(
        auth_url,
        json={"username": username, "password": password},
        headers={"Content-Type": "application/json"},
        timeout=timeout,
        verify=build_verify_option(verify_ssl, ca_bundle_path),
    )
    response.raise_for_status()
    session_id = extract_session_id(response.json())

    LOGGER.info("Authentication succeeded for user=%s", username)
    audit_event("authentication_succeeded", {"auth_url": auth_url, "username": username})
    return session_id
