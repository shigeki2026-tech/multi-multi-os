from datetime import datetime

import streamlit as st

from src.repositories.db import get_session
from src.repositories.master_repository import MasterRepository
from src.ui.bootstrap import ensure_app_ready


NAV_ITEMS = [
    ("\u30db\u30fc\u30e0", "app.py"),
    ("\u30c0\u30c3\u30b7\u30e5\u30dc\u30fc\u30c9", "pages/01_\u30c0\u30c3\u30b7\u30e5\u30dc\u30fc\u30c9.py"),
    ("\u30bf\u30b9\u30af", "pages/02_\u30bf\u30b9\u30af.py"),
    ("SV\u4f9d\u983c", "pages/03_SV\u4f9d\u983c.py"),
    ("\u30ab\u30ec\u30f3\u30c0\u30fc", "pages/04_\u30ab\u30ec\u30f3\u30c0\u30fc.py"),
    ("\u5fdc\u7b54\u7387\u901f\u5831", "pages/05_\u5fdc\u7b54\u7387\u901f\u5831.py"),
    ("\u65e5\u5831\u9001\u4fe1", "pages/06_\u65e5\u5831\u9001\u4fe1.py"),
    ("\u547c\u8a73\u7d30\u4f5c\u6210", "pages/07_\u547c\u8a73\u7d30\u4f5c\u6210.py"),
    ("\u6253\u523b\u7167\u5408", "pages/08_\u6253\u523b\u7167\u5408.py"),
    ("\u901a\u8a71\u9332\u97f3", "pages/09_\u901a\u8a71\u9332\u97f3.py"),
    ("\u7ba1\u7406", "pages/99_\u7ba1\u7406.py"),
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
            st.subheader("\u30ed\u30b0\u30a4\u30f3")
            st.caption("\u5229\u7528\u3059\u308b\u30e6\u30fc\u30b6\u30fc\u3092\u9078\u629e\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
            users = _list_users()
            selected = st.selectbox(
                "\u30e6\u30fc\u30b6\u30fc\u9078\u629e",
                options=users,
                format_func=lambda item: item["label"],
                index=None,
                placeholder="\u30e6\u30fc\u30b6\u30fc\u3092\u9078\u629e",
            )
            if st.button("\u30ed\u30b0\u30a4\u30f3", type="primary"):
                if selected:
                    st.session_state["current_user"] = _login_user(selected["value"])
                    _set_login_query_params(selected["value"])
                    st.session_state.pop("current_user_id", None)
                    st.rerun()
                st.warning("\u30e6\u30fc\u30b6\u30fc\u3092\u9078\u629e\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
    st.stop()


def get_current_user():
    current_user = st.session_state.get("current_user")
    if current_user:
        return current_user

    query_user_id = _get_query_user_id()
    if query_user_id is not None:
        current_user = _fetch_user_dict(query_user_id)
        if current_user:
            st.session_state["current_user"] = current_user
            return current_user
        _clear_login_query_params()

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
    _clear_login_query_params()


def ensure_admin(user=None):
    current_user = user or get_current_user()
    if not current_user or current_user.get("role") != "admin":
        st.error("\u3053\u306e\u753b\u9762\u306f admin \u30ed\u30fc\u30eb\u306e\u307f\u5229\u7528\u3067\u304d\u307e\u3059\u3002")
        st.stop()


def render_sidebar(user: dict):
    _apply_layout_style()
    with st.sidebar:
        st.markdown("### \u30de\u30eb\u30c1\u30de\u30eb\u30c1OS")
        with st.container(border=True):
            st.markdown(f"**{user['display_name']}**")
            role_color = "#2563EB" if user["role"] == "admin" else "#64748B"
            st.markdown(badge(user["role"], role_color), unsafe_allow_html=True)
            st.caption(user["team_name"] or "\u30c1\u30fc\u30e0\u672a\u8a2d\u5b9a")

        st.divider()
        for label, page in NAV_ITEMS:
            if label == "\u7ba1\u7406" and user.get("role") != "admin":
                continue
            st.page_link(page, label=label)

        st.markdown("<div class='sidebar-footer-space'></div>", unsafe_allow_html=True)
        if st.button("\u30ed\u30b0\u30a2\u30a6\u30c8", key="sidebar_logout"):
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
        [data-testid="stAppViewBlockContainer"] h3 {
            font-size: 1.7rem;
            line-height: 1.35;
        }
        [data-testid="stAppViewBlockContainer"] [data-testid="stCaptionContainer"] {
            font-size: 1rem;
            line-height: 1.55;
            color: #374151;
        }
        [data-testid="stAppViewBlockContainer"] [data-testid="stWidgetLabel"] p {
            font-size: 1rem;
            font-weight: 700;
            color: #111827;
        }
        [data-testid="stAppViewBlockContainer"] [data-baseweb="select"] > div {
            min-height: 3rem;
            background: #FFFFFF;
            border: 1px solid #94A3B8;
            box-shadow: inset 0 0 0 1px rgba(148,163,184,0.12);
        }
        [data-testid="stAppViewBlockContainer"] [data-baseweb="select"] span,
        [data-testid="stAppViewBlockContainer"] [data-baseweb="select"] div {
            color: #111827;
            font-size: 1rem;
        }
        [data-testid="stAppViewBlockContainer"] [data-baseweb="select"] input::placeholder {
            color: #6B7280;
            opacity: 1;
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
        .stFormSubmitButton button {
            width: auto !important;
            min-width: 96px;
            border-radius: 10px;
            border: 1px solid #CBD5E1;
            background: #FFFFFF;
            color: #111827;
            box-shadow: none;
        }
        .stFormSubmitButton button:hover {
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
        .stFormSubmitButton button[kind="primary"] {
            background: #2563EB !important;
            color: #FFFFFF !important;
            border-color: #2563EB !important;
        }
        .stFormSubmitButton button[kind="primary"]:hover {
            background: #1D4ED8 !important;
            border-color: #1D4ED8 !important;
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] .stButton:last-of-type button {
            background: #374151;
            color: #F9FAFB;
            border-color: #4B5563;
        }
        .element-container:has(.success-button-marker) + div .stButton button,
        .element-container:has(.success-button-marker) + div .stFormSubmitButton button {
            background: #16A34A !important;
            color: #FFFFFF !important;
            border-color: #16A34A !important;
        }
        .element-container:has(.success-button-marker) + div .stButton button:hover,
        .element-container:has(.success-button-marker) + div .stFormSubmitButton button:hover {
            background: #15803D !important;
            color: #FFFFFF !important;
            border-color: #15803D !important;
        }
        .element-container:has(.danger-button-marker) + div .stButton button,
        .element-container:has(.danger-button-marker) + div .stFormSubmitButton button {
            background: #DC2626 !important;
            color: #FFFFFF !important;
            border-color: #DC2626 !important;
        }
        .element-container:has(.danger-button-marker) + div .stButton button:hover,
        .element-container:has(.danger-button-marker) + div .stFormSubmitButton button:hover {
            background: #B91C1C !important;
            color: #FFFFFF !important;
            border-color: #B91C1C !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _get_query_user_id():
    raw_value = st.query_params.get("user_id")
    if raw_value is None:
        return None
    if isinstance(raw_value, list):
        raw_value = raw_value[0] if raw_value else None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _set_login_query_params(user_id: int):
    st.query_params["user_id"] = str(user_id)


def _clear_login_query_params():
    try:
        st.query_params.clear()
    except AttributeError:
        st.query_params.pop("user_id", None)


def _list_users():
    with get_session() as session:
        repo = MasterRepository(session)
        teams = {team.team_id: team.team_name for team in repo.list_teams()}
        return [
            {
                "value": user.user_id,
                "label": f"{user.display_name} / {user.role} / {teams.get(user.team_id, '\u30c1\u30fc\u30e0\u672a\u8a2d\u5b9a')}",
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
        "team_name": team.team_name if team else "\u30c1\u30fc\u30e0\u672a\u8a2d\u5b9a",
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
    }
