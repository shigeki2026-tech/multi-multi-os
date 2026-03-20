import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_admin, ensure_logged_in, render_sidebar


ROLES = ["admin", "sv"]


def badge(label: str, color: str, filled: bool = True) -> str:
    if filled:
        style = f"background:{color};color:#ffffff;border:1px solid {color};"
    else:
        style = f"background:#ffffff;color:{color};border:1px solid {color};"
    return (
        f"<span style='display:inline-block;padding:0.12rem 0.5rem;margin-right:0.2rem;"
        f"border-radius:999px;font-size:0.76rem;font-weight:700;{style}'>{label}</span>"
    )


def color_chip(color: str) -> str:
    return (
        f"<span style='display:inline-block;width:12px;height:12px;border-radius:999px;"
        f"background:{color};border:1px solid rgba(0,0,0,0.15);margin-right:0.35rem;vertical-align:middle;'></span>"
    )


st.set_page_config(page_title="管理", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
ensure_admin(user)
render_sidebar(user)

with service_scope() as container:
    apps = container.admin_service.list_apps()
    audit_logs = container.audit_service.list_audit_logs_for_display()
    response_history = container.leoc_service.list_history_for_display()
    team_options = container.master_service.team_options()
    team_rows = container.master_service.list_teams_for_admin()
    project_rows = container.master_service.list_projects_for_admin()
    user_rows = container.master_service.list_users_for_admin()

st.title("管理")
st.caption("利用者マスタ、チームマスタ、プロジェクトマスタ、監査ログを確認します。")

project_map = {row["project_id"]: row for row in project_rows}
user_map = {row["user_id"]: row for row in user_rows}
team_map = {row["team_id"]: row for row in team_rows}

st.subheader("ユーザーマスタ")
with st.container(border=True):
    top_cols = st.columns([1.2, 4.8])
    if top_cols[0].button("+ ユーザー追加", type="primary"):
        st.session_state["show_user_create"] = not st.session_state.get("show_user_create", False)
        st.session_state.pop("editing_user_id", None)
        st.rerun()
    top_cols[1].caption("表示名、権限、所属チーム、有効無効を管理します。Googleメールは read-only です。")

    if st.session_state.get("show_user_create", False):
        with st.form("create_user_form", clear_on_submit=True):
            st.markdown("### 新規ユーザー")
            display_name = st.text_input("表示名")
            google_email = st.text_input("Googleメール")
            row1 = st.columns(3)
            role = row1[0].selectbox("権限", ROLES, index=1)
            team = row1[1].selectbox("所属チーム", options=team_options, format_func=lambda item: item["label"])
            is_active = row1[2].checkbox("有効", value=True)
            action = st.columns(2)
            save_user_create = action[0].form_submit_button("追加する", type="primary")
            close_user_create = action[1].form_submit_button("閉じる")
            if close_user_create:
                st.session_state["show_user_create"] = False
                st.rerun()
            if save_user_create:
                if not display_name.strip() or not google_email.strip():
                    st.warning("表示名と Googleメール を入力してください。")
                else:
                    try:
                        with service_scope() as container:
                            container.master_service.create_user(
                                user["user_id"],
                                {
                                    "display_name": display_name.strip(),
                                    "google_email": google_email.strip(),
                                    "role": role,
                                    "team_id": team["value"],
                                    "is_active": is_active,
                                },
                            )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state["show_user_create"] = False
                        st.success("ユーザーを追加しました。")
                        st.rerun()

    header = st.columns([1.4, 1.6, 0.9, 1.3, 0.9, 1.1, 0.8])
    labels = ["表示名", "Googleメール", "権限", "所属チーム", "状態", "最終ログイン", "操作"]
    for col, label in zip(header, labels):
        col.markdown(f"**{label}**")

    for row in user_rows:
        cols = st.columns([1.4, 1.6, 0.9, 1.3, 0.9, 1.1, 0.8])
        cols[0].write(row["display_name"])
        cols[1].caption(row["google_email"])
        cols[2].markdown(
            badge("admin", "#2563EB") if row["role"] == "admin" else badge("sv", "#64748B"),
            unsafe_allow_html=True,
        )
        cols[3].write(row["team_name"])
        cols[4].markdown(
            badge("有効", "#16A34A") if row["is_active"] else badge("無効", "#6B7280"),
            unsafe_allow_html=True,
        )
        cols[5].caption(str(row["last_login_at"] or "-"))
        if cols[6].button("編集", key=f"edit_user_{row['user_id']}"):
            st.session_state["editing_user_id"] = row["user_id"]
            st.session_state["show_user_create"] = False
            st.rerun()

    editing_user_id = st.session_state.get("editing_user_id")
    if editing_user_id and editing_user_id in user_map:
        current = user_map[editing_user_id]
        with st.expander(f"ユーザー編集中: {current['display_name']}", expanded=True):
            with st.form("edit_user_form"):
                display_name = st.text_input("表示名", value=current["display_name"])
                st.text_input("Googleメール", value=current["google_email"], disabled=True)
                row1 = st.columns(3)
                role = row1[0].selectbox("権限", ROLES, index=ROLES.index(current["role"]))
                team = row1[1].selectbox(
                    "所属チーム",
                    options=team_options,
                    index=next((idx for idx, item in enumerate(team_options) if item["value"] == current["team_id"]), 0),
                    format_func=lambda item: item["label"],
                )
                is_active = row1[2].checkbox("有効", value=current["is_active"])
                action = st.columns(2)
                save_user = action[0].form_submit_button("更新する", type="primary")
                close_user = action[1].form_submit_button("閉じる")
                if close_user:
                    st.session_state.pop("editing_user_id", None)
                    st.rerun()
                if save_user:
                    with service_scope() as container:
                        container.master_service.update_user(
                            editing_user_id,
                            user["user_id"],
                            {
                                "display_name": display_name.strip(),
                                "role": role,
                                "team_id": team["value"],
                                "is_active": is_active,
                            },
                        )
                    st.session_state.pop("editing_user_id", None)
                    st.success("ユーザー設定を更新しました。")
                    st.rerun()

st.subheader("チームマスタ")
with st.container(border=True):
    top_cols = st.columns([1.2, 4.8])
    if top_cols[0].button("+ チーム追加", type="primary"):
        st.session_state["show_team_create"] = not st.session_state.get("show_team_create", False)
        st.session_state.pop("editing_team_id", None)
        st.rerun()
    top_cols[1].caption("追加・編集・有効無効変更は監査ログに before / after を保存します。")

    if st.session_state.get("show_team_create", False):
        with st.form("create_team_form", clear_on_submit=True):
            st.markdown("### 新規チーム")
            team_name = st.text_input("チーム名")
            row1 = st.columns(3)
            display_order = row1[0].number_input("表示順", min_value=0, step=10, value=10)
            is_active = row1[1].checkbox("有効", value=True)
            description = row1[2].text_input("説明")
            action = st.columns(2)
            save_team = action[0].form_submit_button("追加する", type="primary")
            close_team = action[1].form_submit_button("閉じる")
            if close_team:
                st.session_state["show_team_create"] = False
                st.rerun()
            if save_team:
                if not team_name.strip():
                    st.warning("チーム名を入力してください。")
                else:
                    with service_scope() as container:
                        container.master_service.create_team(
                            user["user_id"],
                            {
                                "team_name": team_name.strip(),
                                "display_order": int(display_order),
                                "is_active": is_active,
                                "description": description.strip(),
                            },
                        )
                    st.session_state["show_team_create"] = False
                    st.success("チームを追加しました。")
                    st.rerun()

    header = st.columns([1.8, 0.9, 0.9, 1.8, 0.8])
    labels = ["チーム名", "表示順", "状態", "説明", "操作"]
    for col, label in zip(header, labels):
        col.markdown(f"**{label}**")

    for row in team_rows:
        cols = st.columns([1.8, 0.9, 0.9, 1.8, 0.8])
        cols[0].write(row["team_name"])
        cols[1].caption(f"順序 {row['display_order']}")
        cols[2].markdown(
            badge("有効", "#16A34A") if row["is_active"] else badge("無効", "#6B7280"),
            unsafe_allow_html=True,
        )
        cols[3].caption(row["description"] or "-")
        if cols[4].button("編集", key=f"edit_team_{row['team_id']}"):
            st.session_state["editing_team_id"] = row["team_id"]
            st.session_state["show_team_create"] = False
            st.rerun()

    editing_team_id = st.session_state.get("editing_team_id")
    if editing_team_id and editing_team_id in team_map:
        current = team_map[editing_team_id]
        with st.expander(f"チーム編集中: {current['team_name']}", expanded=True):
            with st.form("edit_team_form"):
                team_name = st.text_input("チーム名", value=current["team_name"])
                row1 = st.columns(3)
                display_order = row1[0].number_input("表示順", min_value=0, step=10, value=int(current["display_order"]))
                is_active = row1[1].checkbox("有効", value=current["is_active"])
                description = row1[2].text_input("説明", value=current["description"])
                action = st.columns(2)
                save_edit = action[0].form_submit_button("更新する", type="primary")
                close_edit = action[1].form_submit_button("閉じる")
                if close_edit:
                    st.session_state.pop("editing_team_id", None)
                    st.rerun()
                if save_edit:
                    with service_scope() as container:
                        container.master_service.update_team(
                            editing_team_id,
                            user["user_id"],
                            {
                                "team_name": team_name.strip(),
                                "display_order": int(display_order),
                                "is_active": is_active,
                                "description": description.strip(),
                            },
                        )
                    st.session_state.pop("editing_team_id", None)
                    st.success("チームを更新しました。")
                    st.rerun()

st.subheader("プロジェクトマスタ")
with st.container(border=True):
    top_cols = st.columns([1.2, 4.8])
    if top_cols[0].button("+ プロジェクト追加", type="primary"):
        st.session_state["show_project_create"] = not st.session_state.get("show_project_create", False)
        st.session_state.pop("editing_project_id", None)
        st.rerun()
    top_cols[1].caption("追加・編集・有効無効変更は監査ログに before / after を保存します。")

    if st.session_state.get("show_project_create", False):
        with st.form("create_project_form", clear_on_submit=True):
            st.markdown("### 新規プロジェクト")
            project_name = st.text_input("プロジェクト名")
            row1 = st.columns(3)
            team = row1[0].selectbox("チーム", options=team_options, format_func=lambda x: x["label"])
            color = row1[1].color_picker("色", value="#4F8CFF")
            display_order = row1[2].number_input("表示順", min_value=0, step=10, value=10)
            is_active = st.checkbox("有効", value=True)
            action = st.columns(2)
            save_create = action[0].form_submit_button("追加する", type="primary")
            close_create = action[1].form_submit_button("閉じる")
            if close_create:
                st.session_state["show_project_create"] = False
                st.rerun()
            if save_create:
                if not project_name.strip():
                    st.warning("プロジェクト名を入力してください。")
                else:
                    with service_scope() as container:
                        container.master_service.create_project(
                            user["user_id"],
                            {
                                "project_name": project_name.strip(),
                                "team_id": team["value"],
                                "color": color,
                                "display_order": int(display_order),
                                "is_active": is_active,
                            },
                        )
                    st.session_state["show_project_create"] = False
                    st.success("プロジェクトを追加しました。")
                    st.rerun()

    header = st.columns([2.1, 1.3, 1.0, 0.9, 0.9, 0.8])
    labels = ["プロジェクト", "チーム", "色", "表示順", "状態", "操作"]
    for col, label in zip(header, labels):
        col.markdown(f"**{label}**")

    for row in project_rows:
        cols = st.columns([2.1, 1.3, 1.0, 0.9, 0.9, 0.8])
        cols[0].write(row["project_name"])
        cols[1].write(row["team_name"])
        cols[2].markdown(color_chip(row["color"]), unsafe_allow_html=True)
        cols[3].caption(f"順序 {row['display_order']}")
        cols[4].markdown(
            badge("有効", "#16A34A") if row["is_active"] else badge("無効", "#6B7280"),
            unsafe_allow_html=True,
        )
        if cols[5].button("編集", key=f"edit_project_{row['project_id']}"):
            st.session_state["editing_project_id"] = row["project_id"]
            st.session_state["show_project_create"] = False
            st.rerun()

    editing_project_id = st.session_state.get("editing_project_id")
    if editing_project_id and editing_project_id in project_map:
        current = project_map[editing_project_id]
        with st.expander(f"プロジェクト編集中: {current['project_name']}", expanded=True):
            with st.form("edit_project_form"):
                project_name = st.text_input("プロジェクト名", value=current["project_name"])
                row1 = st.columns(3)
                team = row1[0].selectbox(
                    "チーム",
                    options=team_options,
                    index=next((idx for idx, item in enumerate(team_options) if item["value"] == current["team_id"]), 0),
                    format_func=lambda x: x["label"],
                )
                color = row1[1].color_picker("色", value=current["color"])
                display_order = row1[2].number_input("表示順", min_value=0, step=10, value=int(current["display_order"]))
                is_active = st.checkbox("有効", value=current["is_active"])
                action = st.columns(2)
                save_edit = action[0].form_submit_button("更新する", type="primary")
                close_edit = action[1].form_submit_button("閉じる")
                if close_edit:
                    st.session_state.pop("editing_project_id", None)
                    st.rerun()
                if save_edit:
                    if not project_name.strip():
                        st.warning("プロジェクト名を入力してください。")
                    else:
                        with service_scope() as container:
                            container.master_service.update_project(
                                editing_project_id,
                                user["user_id"],
                                {
                                    "project_name": project_name.strip(),
                                    "team_id": team["value"],
                                    "color": color,
                                    "display_order": int(display_order),
                                    "is_active": is_active,
                                },
                            )
                        st.session_state.pop("editing_project_id", None)
                        st.success("プロジェクトを更新しました。")
                        st.rerun()

st.subheader("アプリ一覧")
st.dataframe(apps, use_container_width=True, hide_index=True)

st.subheader("監査ログ")
st.dataframe(audit_logs, use_container_width=True, hide_index=True)

st.subheader("応答率速報履歴")
st.dataframe(response_history, use_container_width=True, hide_index=True)
