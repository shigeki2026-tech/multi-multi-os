import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_admin, ensure_logged_in


st.set_page_config(page_title="Admin", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
ensure_admin(user)

with service_scope() as container:
    apps = container.admin_service.list_apps()
    audit_logs = container.audit_service.list_audit_logs_for_display()
    leoc_history = container.leoc_service.list_history_for_display()

st.title("管理画面")

st.subheader("アプリ一覧")
st.dataframe(apps, use_container_width=True, hide_index=True)

st.subheader("監査ログ")
st.dataframe(audit_logs, use_container_width=True, hide_index=True)

st.subheader("LEOC履歴")
st.dataframe(leoc_history, use_container_width=True, hide_index=True)
