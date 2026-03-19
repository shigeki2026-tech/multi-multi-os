import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_admin, ensure_logged_in


def color_chip(color: str) -> str:
    return (
        f"<span style='display:inline-block;width:16px;height:16px;border-radius:999px;"
        f"background:{color};border:1px solid rgba(0,0,0,0.15);margin-right:0.45rem;vertical-align:middle;'></span>"
        f"<span style='vertical-align:middle;'>{color}</span>"
    )


st.set_page_config(page_title="管理", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
ensure_admin(user)

with service_scope() as container:
    apps = container.admin_service.list_apps()
    audit_logs = container.audit_service.list_audit_logs_for_display()
    response_history = container.leoc_service.list_history_for_display()
    team_options = container.master_service.team_options()
    project_rows = container.master_service.list_projects_for_admin()

st.title("管理")
st.caption("アプリ設定、プロジェクトマスタ、監査ログをまとめて確認します。")

project_map = {row["project_id"]: row for row in project_rows}

st.subheader("プロジェクトマスタ")
with st.container(border=True):
    if st.button("+ プロジェクト追加", use_container_width=False):
        st.session_state["show_project_create"] = not st.session_state.get("show_project_create", False)
        st.session_state.pop("editing_project_id", None)
        st.rerun()

    if st.session_state.get("show_project_create", False):
        with st.form("create_project_form", clear_on_submit=True):
            project_name = st.text_input("プロジェクト名")
            c1, c2, c3 = st.columns(3)
            team = c1.selectbox("チーム", options=team_options, format_func=lambda x: x["label"])
            color = c2.color_picker("色", value="#5B6CFF")
            display_order = c3.number_input("表示順", min_value=0, step=10, value=10)
            is_active = st.checkbox("有効", value=True)
            submit = st.form_submit_button("追加する", use_container_width=True)
            if submit:
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

    header = st.columns([2.2, 1.2, 1.1, 0.9, 0.8, 0.8])
    labels = ["プロジェクト", "チーム", "色", "表示順", "状態", "操作"]
    for col, label in zip(header, labels):
        col.markdown(f"**{label}**")

    for row in project_rows:
        cols = st.columns([2.2, 1.2, 1.1, 0.9, 0.8, 0.8])
        cols[0].write(row["project_name"])
        cols[1].write(row["team_name"])
        cols[2].markdown(color_chip(row["color"]), unsafe_allow_html=True)
        cols[3].write(row["display_order"])
        cols[4].write("有効" if row["is_active"] else "無効")
        if cols[5].button("編集", key=f"edit_project_{row['project_id']}", use_container_width=True):
            st.session_state["editing_project_id"] = row["project_id"]
            st.session_state["show_project_create"] = False
            st.rerun()

    editing_project_id = st.session_state.get("editing_project_id")
    if editing_project_id and editing_project_id in project_map:
        current = project_map[editing_project_id]
        with st.expander(f"編集中: {current['project_name']}", expanded=True):
            with st.form("edit_project_form"):
                project_name = st.text_input("プロジェクト名", value=current["project_name"])
                c1, c2, c3 = st.columns(3)
                team = c1.selectbox(
                    "チーム",
                    options=team_options,
                    index=next((idx for idx, item in enumerate(team_options) if item["value"] == current["team_id"]), 0),
                    format_func=lambda x: x["label"],
                )
                color = c2.color_picker("色", value=current["color"])
                display_order = c3.number_input("表示順", min_value=0, step=10, value=int(current["display_order"]))
                is_active = st.checkbox("有効", value=current["is_active"])
                update = st.form_submit_button("変更を保存", use_container_width=True)
                if update:
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
            if st.button("編集を閉じる", key="close_project_edit", use_container_width=True):
                st.session_state.pop("editing_project_id", None)
                st.rerun()

st.subheader("アプリ一覧")
st.dataframe(apps, use_container_width=True, hide_index=True)

st.subheader("監査ログ")
st.dataframe(audit_logs, use_container_width=True, hide_index=True)

st.subheader("応答率速報履歴")
st.dataframe(response_history, use_container_width=True, hide_index=True)
