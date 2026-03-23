from __future__ import annotations

import tempfile
from pathlib import Path

from .adapters import ExcelSourceAdapter
from .config import COMPANY_LOOKUP_PATH, LP_DATABASE_PATH
from .service import LookupService


def _build_service_from_uploads(lp_upload, company_upload) -> LookupService:
    temp_dir = Path(tempfile.mkdtemp(prefix="lp_lookup_"))
    lp_path = temp_dir / "Atrea_LP_Database_Export.xlsx"
    company_path = temp_dir / "Company Look-Up.xlsx"
    lp_path.write_bytes(lp_upload.getvalue())
    company_path.write_bytes(company_upload.getvalue())
    return LookupService(ExcelSourceAdapter(lp_database_path=lp_path, company_lookup_path=company_path))


def main() -> None:
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Streamlit is not installed. Run `python3 -m pip install -r requirements.txt` "
            "and then `python3 -m streamlit run app.py`."
        ) from exc

    st.set_page_config(page_title="LP Look-Through Lookup", layout="wide")
    st.title("LP Look-Through Lookup")
    st.caption("Map company investors to fund managers, then surface LP look-through exposure.")

    local_files_available = LP_DATABASE_PATH.exists() and COMPANY_LOOKUP_PATH.exists()
    source_mode = "Local files" if local_files_available else "Uploaded files"
    if local_files_available:
        source_mode = st.radio("Data source", ["Local files", "Uploaded files"], horizontal=True)

    try:
        if source_mode == "Local files":
            service = LookupService()
        else:
            st.info("Upload both Excel files to build a lookup session in the deployed app.")
            lp_upload = st.file_uploader("LP database export", type=["xlsx"], key="lp_upload")
            company_upload = st.file_uploader("Company lookup workbook", type=["xlsx"], key="company_upload")
            if not (lp_upload and company_upload):
                return
            service = _build_service_from_uploads(lp_upload, company_upload)
    except FileNotFoundError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.exception(exc)
        return

    with st.expander("Source Files", expanded=False):
        if source_mode == "Local files":
            for path in service.source_paths:
                exists = Path(path).exists()
                label = "Available" if exists else "Missing"
                st.write(f"- {label}: `{path}`")
        else:
            st.write("- Uploaded workbook session")

    companies = service.list_companies()
    if not companies:
        st.warning("No companies were loaded from the company workbook.")
        return

    selected_company = st.selectbox("Company", companies, index=0)
    summary = service.company_summary(selected_company)

    col1, col2, col3 = st.columns(3)
    col1.metric("Matched Investors", summary["matched_investors"])
    col2.metric("Unmatched Investors", summary["unmatched_investors"])
    col3.metric("Deduped LPs", summary["deduped_lps"])

    exposure_df = service.exposure_dataframe(selected_company)
    match_df = service.match_dataframe(selected_company)
    unmatched_df = service.unmatched_dataframe(selected_company)

    st.subheader("LP Exposure")
    if exposure_df.empty:
        st.info("No LP exposure rows were generated for this company.")
    else:
        st.dataframe(exposure_df, use_container_width=True, hide_index=True)
        st.download_button(
            label="Export LP results as CSV",
            data=service.exposure_csv_bytes(selected_company),
            file_name=f"{selected_company.lower().replace(' ', '_')}_lp_exposure.csv",
            mime="text/csv",
        )

    st.subheader("Accepted Investor Matches")
    if match_df.empty:
        st.info("No investor matches were accepted for this company.")
    else:
        st.dataframe(match_df, use_container_width=True, hide_index=True)

    st.subheader("Unmatched Investors")
    if unmatched_df.empty:
        st.success("All investors for this company produced a match.")
    else:
        st.dataframe(unmatched_df, use_container_width=True, hide_index=True)
