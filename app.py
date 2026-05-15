from __future__ import annotations

import json
from io import BytesIO

import pandas as pd
import streamlit as st

from src.api_tester.auth import authenticate
from src.api_tester.comparison import compare_api_results
from src.api_tester.execution import ExecutionConfig, execute_sheets
from src.api_tester.logging_config import AUDIT_FILE, LOG_FILE, setup_logging
from src.api_tester.reports import build_report_workbook, summarize_report
from src.api_tester.templates import build_template_workbook, read_selected_sheets, supported_sheets


LOGGER = setup_logging()


st.set_page_config(page_title="API Regression Testing", layout="wide")
st.title("API Regression Testing Framework")

if "session_id" not in st.session_state:
    st.session_state.session_id = ""
if "report_df" not in st.session_state:
    st.session_state.report_df = pd.DataFrame()


def render_authentication() -> None:
    st.header("Step 1: Authentication")
    with st.form("auth_form"):
        auth_url = st.text_input("AUTH URL")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        verify_ssl = st.checkbox("Verify SSL certificates", value=True, key="auth_verify_ssl")
        ca_bundle_path = st.text_input(
            "Custom CA bundle path",
            help="Optional path to a PEM/CRT bundle for internal or corporate certificates.",
            key="auth_ca_bundle_path",
        )
        submitted = st.form_submit_button("Authenticate")

    if submitted:
        try:
            st.session_state.session_id = authenticate(
                auth_url,
                username,
                password,
                verify_ssl=verify_ssl,
                ca_bundle_path=ca_bundle_path,
            )
            st.success("Authentication successful. Session ID captured.")
        except Exception as exc:
            LOGGER.exception("Authentication failed")
            st.error(f"Authentication failed: {exc}")
    if not st.session_state.get("auth_verify_ssl", True):
        st.warning("SSL verification is disabled for authentication. Use only in trusted test environments.")

    manual_session = st.text_input(
        "Or paste existing session ID",
        value=st.session_state.session_id,
        type="password",
    )
    st.session_state.session_id = manual_session


def render_template_download() -> None:
    st.header("Step 2: Template Download")
    all_sheets = supported_sheets()
    selected = st.multiselect(
        "Select template sheets",
        options=all_sheets,
        default=all_sheets,
    )
    if selected:
        template = build_template_workbook(selected)
        st.download_button(
            "Download Excel Template",
            data=template,
            file_name="api_testcase_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def render_execution() -> None:
    st.header("Step 3 and 4: Upload and Execute")
    uploaded = st.file_uploader("Upload test case Excel file", type=["xlsx"])
    sheet_mode = st.radio(
        "Sheet selection",
        ["All supported sheets found in workbook", "Choose specific sheets"],
        horizontal=True,
    )
    chosen_sheets = supported_sheets()
    if sheet_mode == "Choose specific sheets":
        chosen_sheets = st.multiselect("Sheets to execute", supported_sheets(), default=supported_sheets())

    col_a, col_b = st.columns(2)
    with col_a:
        timeout = st.number_input("Request timeout seconds", min_value=1, max_value=300, value=60)
    with col_b:
        max_workers = st.number_input("Parallel workers", min_value=1, max_value=50, value=5)
    ignore_order = st.checkbox(
        "Ignore array order in response comparison",
        value=False,
    )
    verify_ssl = st.checkbox("Verify SSL certificates for API execution", value=True)
    ca_bundle_path = st.text_input(
        "Custom CA bundle path for API execution",
        help="Optional path to a PEM/CRT bundle for internal or corporate certificates.",
    )
    if not verify_ssl:
        st.warning("SSL verification is disabled for API execution. Use only in trusted test environments.")

    if uploaded:
        workbook = pd.ExcelFile(uploaded)
        available_supported = [sheet for sheet in supported_sheets() if sheet in workbook.sheet_names]
        if sheet_mode == "All supported sheets found in workbook":
            chosen_sheets = available_supported
        st.caption(f"Workbook sheets: {', '.join(workbook.sheet_names)}")

    if st.button("Execute Test Cases", type="primary"):
        if not uploaded:
            st.error("Upload an Excel file before execution.")
            return
        if not st.session_state.session_id:
            st.error("Authenticate or paste a session ID before execution.")
            return
        if not chosen_sheets:
            st.error("Select at least one supported sheet.")
            return

        try:
            uploaded.seek(0)
            sheets = read_selected_sheets(uploaded, chosen_sheets)
            config = ExecutionConfig(
                session_id=st.session_state.session_id,
                timeout=int(timeout),
                max_workers=int(max_workers),
                ignore_order=ignore_order,
                verify_ssl=verify_ssl,
                ca_bundle_path=ca_bundle_path,
            )
            with st.spinner("Executing old and new API calls in parallel..."):
                st.session_state.report_df = execute_sheets(sheets, config)
            st.success("Execution completed.")
        except Exception as exc:
            LOGGER.exception("Execution failed")
            st.error(f"Execution failed: {exc}")

    if not st.session_state.report_df.empty:
        report_df = st.session_state.report_df
        summary = summarize_report(report_df)
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Total", summary["total"])
        c2.metric("Passed", summary["passed"])
        c3.metric("Failed", summary["failed"])
        c4.metric("Status Mismatch", summary["status_mismatches"])
        c5.metric("Response Mismatch", summary["response_mismatches"])
        c6.metric("Performance Passed", summary["performance_passed"])
        c7.metric("Performance Failed", summary["performance_failed"])

        st.dataframe(report_df, use_container_width=True)
        report = build_report_workbook(report_df)
        st.download_button(
            "Download Validation Report",
            data=report,
            file_name="api_validation_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def render_comparison_lab() -> None:
    st.header("Comparison Lab")
    st.caption("Use this area to test status, response, and performance comparison logic without calling APIs.")
    default_old = json.dumps({"claimId": 101, "status": "OPEN", "items": [{"id": 1, "amount": 50}]}, indent=2)
    default_new = json.dumps({"claimId": 101, "status": "CLOSED", "items": [{"id": 1, "amount": 50}]}, indent=2)

    col_a, col_b = st.columns(2)
    with col_a:
        old_status = st.number_input("Old status", value=200)
        old_ms = st.number_input("Old elapsed ms", value=120.0)
        old_body = st.text_area("Old response body", value=default_old, height=260)
    with col_b:
        new_status = st.number_input("New status", value=200)
        new_ms = st.number_input("New elapsed ms", value=95.0)
        new_body = st.text_area("New response body", value=default_new, height=260)

    if st.button("Compare Sample Responses"):
        result = compare_api_results(
            {"status_code": old_status, "response_text": old_body, "elapsed_ms": old_ms},
            {"status_code": new_status, "response_text": new_body, "elapsed_ms": new_ms},
        )
        st.json(result)


def render_logs() -> None:
    st.header("Logs and Audit Trail")
    col_a, col_b = st.columns(2)
    with col_a:
        if LOG_FILE.exists():
            st.download_button("Download App Log", LOG_FILE.read_bytes(), file_name="api_testing.log")
        else:
            st.info("No app log written yet.")
    with col_b:
        if AUDIT_FILE.exists():
            st.download_button("Download Audit Trail", AUDIT_FILE.read_bytes(), file_name="audit_trail.jsonl")
        else:
            st.info("No audit trail written yet.")


tab_main, tab_lab, tab_logs = st.tabs(["API Testing", "Comparison Lab", "Logs"])
with tab_main:
    render_authentication()
    render_template_download()
    render_execution()
with tab_lab:
    render_comparison_lab()
with tab_logs:
    render_logs()
