import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar


def render_summary_card(title: str, value):
    with st.container(border=True):
        st.caption(title)
        st.metric(title, value, label_visibility="collapsed")


def render_empty_state(message: str):
    with st.container(border=True):
        st.caption(message)


st.set_page_config(page_title="ダッシュボード", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

with service_scope() as container:
    dashboard = container.dashboard_service.get_dashboard_data(user["user_id"])
    apps = container.admin_service.list_apps()

st.title("ダッシュボード")

calendar_status = dashboard["calendar_status"]
event_metric = "取得失敗" if calendar_status["error"] else len(dashboard["today_events"])

summary_cols = st.columns(5)
with summary_cols[0]:
    render_summary_card("今日やること", dashboard["today_count"])
with summary_cols[1]:
    render_summary_card("未確認SV依頼", dashboard["unack_requests"])
with summary_cols[2]:
    render_summary_card("期限超過タスク", dashboard["overdue_count"])
with summary_cols[3]:
    render_summary_card("本日の予定", event_metric)
with summary_cols[4]:
    render_summary_card("最新の応答率", dashboard["latest_leoc_rate"])

left, right = st.columns([1.45, 1], gap="large")
with left:
    st.subheader("今日やること")
    if dashboard["today_items"]:
        st.dataframe(dashboard["today_items"], use_container_width=True, hide_index=True)
    else:
        render_empty_state("現在対象なし")

    st.subheader("期限超過タスク")
    if dashboard["overdue_items"]:
        st.dataframe(dashboard["overdue_items"], use_container_width=True, hide_index=True)
    else:
        render_empty_state("現在対象なし")

with right:
    st.subheader("本日の予定")
    with st.container(border=True):
        if calendar_status["error"]:
            st.warning(calendar_status["message"])
        elif calendar_status["using_mock"]:
            st.info(calendar_status["message"])

        if dashboard["today_events"]:
            for event in dashboard["today_events"]:
                st.info(f'{event["time"]} | {event["title"]}')
        else:
            st.caption("本日の予定はありません。")

    st.subheader("応答率速報")
    with st.container(border=True):
        if dashboard["latest_leoc"]:
            st.code(dashboard["latest_leoc"]["post_text"], language="text")
        else:
            st.caption("現在対象なし")

st.subheader("クイック起動")
quick_cols = st.columns(5)
for idx, app in enumerate(apps[:5]):
    with quick_cols[idx]:
        with st.container(border=True):
            st.caption(app["app_name"])
            st.page_link(app["page"], label="開く", icon=":material/open_in_new:")
