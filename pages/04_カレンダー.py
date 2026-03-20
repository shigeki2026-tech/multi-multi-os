import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar


st.set_page_config(page_title="カレンダー", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

with service_scope() as container:
    today_events = container.calendar_service.get_todays_events(user["user_id"])
    week_events = container.calendar_service.get_week_events(user["user_id"])
    calendar_status = container.calendar_service.get_status()

st.title("カレンダー")

if calendar_status["error"]:
    st.warning(calendar_status["message"])
elif calendar_status["using_mock"]:
    st.info(calendar_status["message"])
else:
    st.success(calendar_status["message"])

left, right = st.columns(2)
with left:
    st.subheader("本日の予定")
    if today_events:
        st.dataframe(today_events, use_container_width=True, hide_index=True)
    else:
        st.caption("本日の予定はありません。")

with right:
    st.subheader("今週の予定")
    if week_events:
        st.dataframe(week_events, use_container_width=True, hide_index=True)
    else:
        st.caption("今週の予定は取得できませんでした。")

st.caption("API 未設定または取得失敗時は警告を表示し、アプリ全体は継続して利用できます。")
