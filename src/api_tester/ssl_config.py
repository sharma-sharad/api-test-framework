from __future__ import annotations


def build_verify_option(verify_ssl: bool = True, ca_bundle_path: str | None = None) -> bool | str:
    if not verify_ssl:
        return False
    if ca_bundle_path and ca_bundle_path.strip():
        return ca_bundle_path.strip()
    return True
