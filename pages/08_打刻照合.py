import pandas as pd
import streamlit as st

from src.services.attendance_service import (
    LABEL_ACTUAL,
    LABEL_DATE,
    LABEL_EARLY,
    LABEL_EXPECTED,
    LABEL_LATE,
    LABEL_NAME,
    LABEL_NOTE,
    LABEL_OVERTIME,
    LABEL_RESULT,
    LABEL_SHIFT_RAW,
    STATUS_MATCH,
)
from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar
from src.utils.attendance_parser import to_csv_bytes, to_export_bytes


DISPLAY_COLUMNS = [
    LABEL_DATE,
    "ID",
    LABEL_NAME,
    "Team",
    "Post",
    LABEL_SHIFT_RAW,
    LABEL_EXPECTED,
    LABEL_ACTUAL,
    LABEL_LATE,
    LABEL_EARLY,
    LABEL_OVERTIME,
    LABEL_RESULT,
    LABEL_NOTE,
]


st.set_page_config(page_title="\u6253\u523b\u7167\u5408", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("\u6253\u523b\u7167\u5408")
st.caption("\u6708\u6b21\u7de0\u3081\u5411\u3051\u306b\u3001\u30b7\u30d5\u30c8\u8868\u3068\u6253\u523b\u5b9f\u7e3e\u3092\u7167\u5408\u3057\u3066\u5dee\u7570\u3060\u3051\u3092\u4e00\u89a7\u5316\u3057\u307e\u3059\u3002")

with service_scope() as container:
    recent_runs = container.attendance_service.list_recent_runs_for_display()

with st.container(border=True):
    st.subheader("\u7167\u5408\u5b9f\u884c")
    left, right = st.columns(2)
    target_label = left.text_input("\u6708\u5ea6\u307e\u305f\u306f\u7de0\u3081\u5bfe\u8c61\u671f\u9593", value=st.session_state.get("attendance_target_label", ""))
    shift_input_mode = left.radio(
        "\u30b7\u30d5\u30c8\u5165\u529b\u65b9\u6cd5",
        options=["file", "paste"],
        format_func=lambda value: "\u30d5\u30a1\u30a4\u30eb\u30a2\u30c3\u30d7\u30ed\u30fc\u30c9" if value == "file" else "Excel\u8cbc\u308a\u4ed8\u3051",
        horizontal=True,
    )
    shift_file = left.file_uploader("\u30b7\u30d5\u30c8\u30d5\u30a1\u30a4\u30eb", type=["csv", "xlsx", "xls"])
    shift_text = left.text_area(
        "Excel \u8cbc\u308a\u4ed8\u3051\u30c6\u30ad\u30b9\u30c8",
        value=st.session_state.get("attendance_shift_text", ""),
        height=180,
        placeholder="Excel \u304b\u3089\u30b7\u30d5\u30c8\u8868\u3092\u305d\u306e\u307e\u307e\u30b3\u30d4\u30fc\u3057\u3066\u8cbc\u308a\u4ed8\u3051",
    )
    punch_file = right.file_uploader("\u6253\u523bCSV", type=["csv", "xlsx", "xls"])
    run_button = st.button("\u7167\u5408\u5b9f\u884c", type="primary")

if run_button:
    if not punch_file:
        st.warning("\u6253\u523b\u30d5\u30a1\u30a4\u30eb\u3092\u9078\u629e\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
    elif shift_input_mode == "paste" and not shift_text.strip():
        st.warning("\u8cbc\u308a\u4ed8\u3051\u30b7\u30d5\u30c8\u30c6\u30ad\u30b9\u30c8\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
    elif shift_input_mode == "file" and not shift_file:
        st.warning("\u30b7\u30d5\u30c8\u30d5\u30a1\u30a4\u30eb\u3092\u9078\u629e\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
    else:
        try:
            with service_scope() as container:
                result = container.attendance_service.run_reconciliation(
                    actor_id=user["user_id"],
                    target_label=target_label,
                    punch_file=punch_file,
                    shift_file=shift_file,
                    shift_text=shift_text,
                    shift_input_mode=shift_input_mode,
                )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state["attendance_target_label"] = target_label
            st.session_state["attendance_shift_text"] = shift_text
            st.session_state["attendance_result"] = result
            st.success(f"\u7167\u5408\u304c\u5b8c\u4e86\u3057\u307e\u3057\u305f\u3002\u5dee\u7570 {result['summary']['\u5dee\u7570\u7dcf\u4ef6\u6570']} \u4ef6\u3067\u3059\u3002")
            st.rerun()

result = st.session_state.get("attendance_result")
if result:
    summary = result["summary"]
    metric_cols = st.columns(6)
    metric_cols[0].metric("\u9045\u523b\u4ef6\u6570", summary["\u9045\u523b\u4ef6\u6570"])
    metric_cols[1].metric("\u65e9\u9000\u4ef6\u6570", summary["\u65e9\u9000\u4ef6\u6570"])
    metric_cols[2].metric("\u6b8b\u696d\u4ef6\u6570", summary["\u6b8b\u696d\u4ef6\u6570"])
    metric_cols[3].metric("\u52e4\u52d9\u4e88\u5b9a\u3060\u304c\u5b9f\u7e3e\u306a\u3057", summary["\u52e4\u52d9\u4e88\u5b9a\u3060\u304c\u5b9f\u7e3e\u306a\u3057\u4ef6\u6570"])
    metric_cols[4].metric("\u4f11\u307f\u30fb\u6709\u7d66\u3060\u304c\u5b9f\u7e3e\u3042\u308a", summary["\u4f11\u307f\u30fb\u6709\u7d66\u3060\u304c\u5b9f\u7e3e\u3042\u308a\u4ef6\u6570"])
    metric_cols[5].metric("\u8981\u78ba\u8a8d", summary["\u8981\u78ba\u8a8d\u4ef6\u6570"])

    st.subheader("\u5dee\u7570\u4e00\u89a7")
    all_rows_df = pd.DataFrame(result["all_rows"])
    if all_rows_df.empty:
        all_rows_df = pd.DataFrame(columns=DISPLAY_COLUMNS + ["_work_date", "_excluded"])
    else:
        all_rows_df = all_rows_df.sort_values(by=[LABEL_NAME, "_work_date"], kind="stable").reset_index(drop=True)

    filter_cols = st.columns(6)
    team_options = ["\u3059\u3079\u3066"] + sorted(value for value in all_rows_df["Team"].dropna().unique().tolist() if value and value != "-")
    post_options = ["\u3059\u3079\u3066"] + sorted(value for value in all_rows_df["Post"].dropna().unique().tolist() if value and value != "-")
    judge_options = ["\u3059\u3079\u3066"] + sorted(value for value in all_rows_df[LABEL_RESULT].dropna().unique().tolist() if value and value != STATUS_MATCH)

    selected_team = filter_cols[0].selectbox("Team", team_options)
    selected_post = filter_cols[1].selectbox("Post", post_options)
    selected_judge = filter_cols[2].selectbox("\u5224\u5b9a\u533a\u5206", judge_options)
    name_keyword = filter_cols[3].text_input("\u6c0f\u540d\u691c\u7d22")
    show_all = filter_cols[4].toggle("\u5168\u4ef6\u8868\u793a", value=False)
    include_excluded = filter_cols[5].toggle("\u9664\u5916\u5bfe\u8c61\u3092\u542b\u3080", value=False)

    filtered_df = all_rows_df.copy()
    if not include_excluded:
        filtered_df = filtered_df[filtered_df["_excluded"] == False]
    if not show_all:
        filtered_df = filtered_df[filtered_df[LABEL_RESULT] != STATUS_MATCH]
    if selected_team != "\u3059\u3079\u3066":
        filtered_df = filtered_df[filtered_df["Team"] == selected_team]
    if selected_post != "\u3059\u3079\u3066":
        filtered_df = filtered_df[filtered_df["Post"] == selected_post]
    if selected_judge != "\u3059\u3079\u3066":
        filtered_df = filtered_df[filtered_df[LABEL_RESULT] == selected_judge]
    if name_keyword.strip():
        filtered_df = filtered_df[filtered_df[LABEL_NAME].str.contains(name_keyword.strip(), case=False, na=False)]

    st.dataframe(filtered_df[DISPLAY_COLUMNS], use_container_width=True, hide_index=True)

    export_rows = filtered_df[DISPLAY_COLUMNS].to_dict(orient="records")
    summary_rows = [{"\u9805\u76ee": key, "\u5024": value} for key, value in summary.items()]
    excel_bytes = to_export_bytes(summary_rows, export_rows, result["settings_rows"])
    csv_bytes = to_csv_bytes(export_rows)

    download_cols = st.columns(2)
    download_cols[0].download_button(
        "Excel \u51fa\u529b",
        data=excel_bytes,
        file_name=f"attendance_reconciliation_{result['run_id']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    download_cols[1].download_button(
        "CSV \u51fa\u529b",
        data=csv_bytes,
        file_name=f"attendance_reconciliation_{result['run_id']}.csv",
        mime="text/csv",
    )

st.subheader("\u5b9f\u884c\u5c65\u6b74")
st.dataframe(recent_runs, use_container_width=True, hide_index=True)
