import streamlit as st

from src.repositories.db import get_session
from src.repositories.master_repository import MasterRepository
from src.ui.bootstrap import ensure_app_ready


def ensure_logged_in():
    ensure_app_ready()

    current_user = get_current_user()
    if current_user:
        return current_user

    st.subheader("ダミーログイン")
    users = _list_users()
    selected = st.selectbox("ユーザー選択", options=users, format_func=lambda x: x["label"], index=None)
    if st.button("ログイン", use_container_width=True) and selected:
        st.session_state["current_user"] = _fetch_user_dict(selected["value"])
        st.session_state.pop("current_user_id", None)
        st.rerun()
    st.stop()


def get_current_user():
    current_user = st.session_state.get("current_user")
    if current_user:
        return current_user

    legacy_user_id = st.session_state.get("current_user_id")
    if legacy_user_id:
        current_user = _fetch_user_dict(legacy_user_id)
        if current_user:
            st.session_state["current_user"] = current_user
        st.session_state.pop("current_user_id", None)
        return current_user

    return None


def logout():
    st.session_state.pop("current_user", None)
    st.session_state.pop("current_user_id", None)


def ensure_admin(user=None):
    current_user = user or get_current_user()
    if not current_user or current_user.get("role") != "admin":
        st.error("この画面は admin ロールのみ閲覧できます。")
        st.stop()


def _list_users():
    with get_session() as session:
        repo = MasterRepository(session)
        return [{"value": x.user_id, "label": x.display_name} for x in repo.list_users()]


def _fetch_user_dict(user_id: int):
    with get_session() as session:
        repo = MasterRepository(session)
        user = repo.get_user(user_id)
        if not user:
            return None
        return {
            "user_id": user.user_id,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
        }
