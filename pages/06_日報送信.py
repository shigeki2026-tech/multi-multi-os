from datetime import date

import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar


st.set_page_config(page_title="日報送信", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("日報送信")

with service_scope() as container:
    report_status = container.report_service.get_status()
    history = container.report_service.list_history_for_display()
    default_to = container.config.report_default_to

if report_status["configured"]:
    st.success(report_status["message"])
else:
    st.info(report_status["message"])

with st.form("report_form"):
    c1, c2 = st.columns(2)
    target_date = c1.date_input("対象日", value=date.today())
    subject = c2.text_input("件名", value=f"{target_date} 日報")
    to_addresses = st.text_input("送信先", value=default_to, help="カンマ区切りで複数指定できます。")
    summary = st.text_area("本日の要約", height=100)
    highlights = st.text_area("対応内容", height=140)
    issues = st.text_area("課題・共有事項", height=100)
    next_actions = st.text_area("翌日の対応", height=100)
    preview_clicked = st.form_submit_button("プレビュー作成", type="primary")

if preview_clicked:
    with service_scope() as container:
        preview = container.report_service.build_preview(
            actor_id=user["user_id"],
            payload={
                "report_type": "daily_report",
                "target_date": target_date,
                "subject": subject,
                "to_addresses": to_addresses,
                "summary": summary,
                "highlights": highlights,
                "issues": issues,
                "next_actions": next_actions,
            },
        )
    st.session_state["report_preview"] = preview
    st.session_state["report_payload"] = {
        "report_type": "daily_report",
        "target_date": target_date,
        "subject": subject,
        "to_addresses": to_addresses,
        "summary": summary,
        "highlights": highlights,
        "issues": issues,
        "next_actions": next_actions,
    }

preview = st.session_state.get("report_preview")
payload = st.session_state.get("report_payload")

if preview:
    st.subheader("送信プレビュー")
    st.text_input("送信先確認", value=", ".join(preview["to_addresses"]), disabled=True)
    st.text_input("件名確認", value=preview["subject"], disabled=True)
    if preview["invalid_to_addresses"]:
        st.warning(f"不正な宛先があります: {', '.join(preview['invalid_to_addresses'])}")
    st.text_area("本文プレビュー", value=preview["body"], height=320)
    if st.button("Gmailで送信"):
        try:
            with service_scope() as container:
                result = container.report_service.send_report(actor_id=user["user_id"], payload=payload)
        except Exception as exc:
            st.error(f"送信処理中に予期しないエラーが発生しました: {exc}")
        else:
            if result["send_status"] == "sent":
                st.success(result["message"])
            elif result["send_status"] == "draft":
                st.warning(result["message"])
            else:
                detail = f" 詳細: {result['error_message']}" if result["error_message"] else ""
                st.error(result["message"] + detail)
            st.session_state["report_preview"] = result["preview"]
            st.rerun()

st.subheader("送信履歴")
st.dataframe(history, use_container_width=True, hide_index=True)
