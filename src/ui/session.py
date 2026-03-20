from datetime import datetime

import streamlit as st

from src.repositories.db import get_session
from src.repositories.master_repository import MasterRepository
from src.ui.bootstrap import ensure_app_ready


NAV_ITEMS = [
    ("ホーム", "app.py"),
    ("ダッシュボード", "pages/01_ダッシュボード.py"),
    ("タスク", "pages/02_タスク.py"),
    ("SV依頼", "pages/03_SV依頼.py"),
    ("カレンダー", "pages/04_カレンダー.py"),
    ("応答率速報", "pages/05_応答率速報.py"),
    ("日報送信", "pages/06_日報送信.py"),
    ("呼詳細作成", "pages/07_呼詳細作成.py"),
    ("管理", "pages/99_管理.py"),
]


def badge(label: str, color: str, filled: bool = True) -> str:
    if filled:
        style = f"background:{color};color:#ffffff;border:1px solid {color};"
    else:
        style = f"background:#ffffff;color:{color};border:1px solid {color};"
    return (
        f"<span style='display:inline-block;padding:0.12rem 0.45rem;"
        f"border-radius:999px;font-size:0.72rem;font-weight:700;{style}'>{label}</span>"
    )


def ensure_logged_in():
    ensure_app_ready()

    current_user = get_current_user()
    if current_user:
        return current_user

    _apply_layout_style()
    left, center, right = st.columns([1.1, 1.4, 1.1])
    with center:
        with st.container(border=True):
            st.subheader("ログイン")
            st.caption("利用するユーザーを選択してください。")
            users = _list_users()
            selected = st.selectbox(
                "ユーザー選択",
                options=users,
                format_func=lambda item: item["label"],
                index=None,
                placeholder="ユーザーを選択",
            )
            if st.button("ログイン", type="primary"):
                if selected:
                    st.session_state["current_user"] = _login_user(selected["value"])
                    st.session_state.pop("current_user_id", None)
                    st.rerun()
                st.warning("ユーザーを選択してください。")
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


def render_sidebar(user: dict):
    _apply_layout_style()
    with st.sidebar:
        st.markdown("### 業務メニュー")
        with st.container(border=True):
            st.markdown(f"**{user['display_name']}**")
            role_color = "#2563EB" if user["role"] == "admin" else "#64748B"
            st.markdown(badge(user["role"], role_color), unsafe_allow_html=True)
            st.caption(user["team_name"] or "チーム未設定")

        st.divider()
        for label, page in NAV_ITEMS:
            if label == "管理" and user.get("role") != "admin":
                continue
            st.page_link(page, label=label)

        st.markdown("<div class='sidebar-footer-space'></div>", unsafe_allow_html=True)
        if st.button("ログアウト", key="sidebar_logout"):
            logout()
            st.rerun()


def _apply_layout_style():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebarNavSeparator"] { display: none; }
        [data-testid="stSidebarHeader"] { display: none; }
        [data-testid="stAppViewContainer"] { background: #F3F4F6; }
        [data-testid="stSidebar"] { background: #1F2937; }
        [data-testid="stSidebar"] * { color: #F9FAFB; }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
            border-radius: 10px;
            padding: 0.35rem 0.55rem;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
            background: rgba(255,255,255,0.08);
        }
        [data-testid="stSidebar"] .sidebar-footer-space {
            min-height: 2.5rem;
        }
        .stButton button {
            width: auto !important;
            min-width: 96px;
            border-radius: 10px;
            border: 1px solid #CBD5E1;
            background: #FFFFFF;
            color: #111827;
            box-shadow: none;
        }
        .stButton button:hover {
            border-color: #94A3B8;
            color: #111827;
        }
        .stButton button[kind="primary"] {
            background: #2563EB;
            color: #FFFFFF;
            border-color: #2563EB;
        }
        .stButton button[kind="primary"]:hover {
            background: #1D4ED8;
            border-color: #1D4ED8;
            color: #FFFFFF;
        }
        [data-testid="stSidebar"] .stButton:last-of-type button {
            background: #374151;
            color: #F9FAFB;
            border-color: #4B5563;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _list_users():
    with get_session() as session:
        repo = MasterRepository(session)
        teams = {team.team_id: team.team_name for team in repo.list_teams()}
        return [
            {
                "value": user.user_id,
                "label": f"{user.display_name} / {user.role} / {teams.get(user.team_id, 'チーム未設定')}",
            }
            for user in repo.list_users(active_only=True)
        ]


def _login_user(user_id: int):
    with get_session() as session:
        repo = MasterRepository(session)
        user = repo.get_user(user_id)
        if not user:
            return None
        user.last_login_at = datetime.utcnow()
        repo.update_last_login(user)
        return _to_user_dict(user, repo)


def _fetch_user_dict(user_id: int):
    with get_session() as session:
        repo = MasterRepository(session)
        user = repo.get_user(user_id)
        if not user:
            return None
        return _to_user_dict(user, repo)


def _to_user_dict(user, repo: MasterRepository):
    team = repo.get_team(user.team_id)
    return {
        "user_id": user.user_id,
        "google_email": user.google_email,
        "display_name": user.display_name,
        "email": user.email,
        "role": user.role,
        "team_id": user.team_id,
        "team_name": team.team_name if team else "チーム未設定",
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
    }
