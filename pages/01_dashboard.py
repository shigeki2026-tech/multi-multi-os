import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in


st.set_page_config(page_title="Dashboard", layout="wide")
ensure_app_ready()
user = ensure_logged_in()

with service_scope() as container:
    dashboard = container.dashboard_service.get_dashboard_data(user["user_id"])
    apps = container.admin_service.list_apps()

st.title("ホームダッシュボード")

calendar_status = dashboard["calendar_status"]
event_metric = "取得失敗" if calendar_status["error"] else len(dashboard["today_events"])

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("今日やること", dashboard["today_count"])
col2.metric("未確認SV依頼", dashboard["unack_requests"])
col3.metric("期限超過タスク", dashboard["overdue_count"])
col4.metric("本日の予定", event_metric)
col5.metric("最新LEOC応答率", dashboard["latest_leoc_rate"])

left, right = st.columns([1.4, 1])
with left:
    st.subheader("今日やること")
    st.dataframe(dashboard["today_items"], use_container_width=True, hide_index=True)

    st.subheader("期限超過タスク")
    st.dataframe(dashboard["overdue_items"], use_container_width=True, hide_index=True)

with right:
    st.subheader("本日の予定")
    if calendar_status["error"]:
        st.warning(calendar_status["message"])
    elif calendar_status["using_mock"]:
        st.info(calendar_status["message"])

    if dashboard["today_events"]:
        for event in dashboard["today_events"]:
            st.info(f'{event["time"]} | {event["title"]}')
    else:
        st.caption("本日の予定はありません。")

    st.subheader("LEOC速報")
    if dashboard["latest_leoc"]:
        st.code(dashboard["latest_leoc"]["post_text"], language="text")
    else:
        st.caption("履歴はまだありません。")

st.subheader("クイック起動")
quick_cols = st.columns(5)
for idx, app in enumerate(apps[:5]):
    quick_cols[idx].page_link(app["page"], label=app["app_name"], use_container_width=True)
