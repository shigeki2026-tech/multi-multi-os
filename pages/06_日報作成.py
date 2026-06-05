import streamlit as st

st.set_page_config(page_title="日報作成", layout="wide")

from datetime import date

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar

ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("日報作成")
st.caption("日報を作成し、プレビュー・コピー・ファイル出力・履歴保存を行います。Gmail送信は会社方針により既定で無効です。")

with service_scope() as container:
    history = container.report_service.list_history_for_display()
    default_to = container.config.report_default_to
    gmail_enabled = container.config.gmail_enabled
    gmail_status = container.report_service.get_status() if gmail_enabled else None

with st.form("report_form"):
    c1, c2 = st.columns(2)
    target_date = c1.date_input("対象日", value=date.today())
    subject = c2.text_input("件名", value=f"{target_date} 日報")
    summary = st.text_area("本日の要約", height=100)
    highlights = st.text_area("対応内容", height=140)
    issues = st.text_area("課題・共有事項", height=100)
    next_actions = st.text_area("翌日の対応", height=100)
    # 送信先は Gmail 有効時のみ意味を持つ。無効時は入力欄を出さない。
    to_addresses = st.text_input("送信先", value=default_to, help="カンマ区切りで複数指定できます。") if gmail_enabled else ""
    preview_clicked = st.form_submit_button("プレビュー作成", type="primary")

if preview_clicked:
    payload = {
        "report_type": "daily_report",
        "target_date": target_date,
        "subject": subject,
        "to_addresses": to_addresses,
        "summary": summary,
        "highlights": highlights,
        "issues": issues,
        "next_actions": next_actions,
    }
    with service_scope() as container:
        preview = container.report_service.build_preview(actor_id=user["user_id"], payload=payload)
    st.session_state["report_preview"] = preview
    st.session_state["report_payload"] = payload

preview = st.session_state.get("report_preview")
payload = st.session_state.get("report_payload")

if preview:
    st.subheader("プレビュー")
    st.text_input("件名確認", value=preview["subject"], disabled=True)
    st.text_area("本文プレビュー", value=preview["body"], height=320)

    st.subheader("コピー / ファイル出力")
    st.text_area("コピー用テキスト", value=preview["body"], height=200, key="report_copy_area")
    file_name = f"{payload['target_date']}_日報.txt"
    st.download_button(
        "ファイル出力（.txt）",
        data=preview["body"].encode("utf-8"),
        file_name=file_name,
        mime="text/plain",
    )

    if st.button("履歴に保存", type="primary"):
        with service_scope() as container:
            result = container.report_service.save_draft(actor_id=user["user_id"], payload=payload)
        st.success(result["message"])
        st.rerun()

    # --- Gmail送信は feature flag (GMAIL_ENABLED) の裏。OFF時はボタンを表示しない ---
    if gmail_enabled:
        st.subheader("Gmail送信（任意）")
        st.text_input("送信先確認", value=", ".join(preview["to_addresses"]), disabled=True)
        if preview["invalid_to_addresses"]:
            st.warning(f"不正な宛先があります: {', '.join(preview['invalid_to_addresses'])}")
        if gmail_status and gmail_status["configured"]:
            st.success(gmail_status["message"])
        elif gmail_status:
            st.info(gmail_status["message"])
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

st.subheader("履歴")
st.dataframe(history, use_container_width=True, hide_index=True)
