from __future__ import annotations

from pathlib import Path

from .config import COMPANY_LOOKUP_PATH, LP_DATABASE_PATH
from .service import LookupService


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

    @st.cache_resource(show_spinner="Loading LP mapping data...")
    def get_service(lp_mtime_ns: int, company_mtime_ns: int) -> LookupService:
        del lp_mtime_ns, company_mtime_ns
        return LookupService()

    try:
        service = get_service(
            LP_DATABASE_PATH.stat().st_mtime_ns,
            COMPANY_LOOKUP_PATH.stat().st_mtime_ns,
        )
    except FileNotFoundError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.exception(exc)
        return

    with st.expander("Source Files", expanded=False):
        for path in service.source_paths:
            exists = Path(path).exists()
            label = "Available" if exists else "Missing"
            st.write(f"- {label}: `{path}`")

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
