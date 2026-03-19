import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in


TASK_TYPES = ["personal_task", "team_task", "handover_task", "sv_request", "recurring_task"]
STATUSES = ["未着手", "確認待ち", "進行中", "保留", "完了", "取消"]
PRIORITIES = ["高", "中", "低"]

st.set_page_config(page_title="Tasks", layout="wide")
ensure_app_ready()
user = ensure_logged_in()

st.title("タスク管理")

with service_scope() as container:
    user_options = container.master_service.user_options()
    team_options = container.master_service.team_options()
    project_options = container.master_service.project_options()

with st.expander("絞り込み", expanded=True):
    f1, f2, f3, f4 = st.columns(4)
    filters = {
        "mine_only": f1.checkbox("自分のタスク", value=True),
        "today_due": f2.checkbox("今日期限"),
        "overdue_only": f3.checkbox("期限超過"),
        "exclude_completed": f4.checkbox("完了を除外", value=True),
    }

with service_scope() as container:
    tasks_df = container.task_service.list_tasks_for_display(user["user_id"], filters)
st.dataframe(tasks_df, use_container_width=True, hide_index=True)

st.subheader("タスク新規作成")
with st.form("create_task_form", clear_on_submit=True):
    title = st.text_input("件名")
    description = st.text_area("内容")
    c1, c2, c3, c4 = st.columns(4)
    task_type = c1.selectbox("種別", TASK_TYPES)
    priority = c2.selectbox("優先度", PRIORITIES)
    status = c3.selectbox("ステータス", STATUSES, index=0)
    assignee = c4.selectbox("担当者", options=user_options, format_func=lambda x: x["label"])
    c5, c6, c7 = st.columns(3)
    team = c5.selectbox("チーム", options=team_options, format_func=lambda x: x["label"])
    project = c6.selectbox("プロジェクト", options=project_options, format_func=lambda x: x["label"])
    due_date = c7.date_input("期限日", value=None)
    related_link = st.text_input("関連リンク")
    needs_confirmation = st.checkbox("確認が必要")
    submit = st.form_submit_button("作成", use_container_width=True)
    if submit and title:
        with service_scope() as container:
            container.task_service.create_task(
                actor_id=user["user_id"],
                payload={
                    "task_type": task_type,
                    "title": title,
                    "description": description,
                    "requester_user_id": user["user_id"],
                    "assignee_user_id": assignee["value"],
                    "team_id": team["value"],
                    "project_id": project["value"],
                    "priority": priority,
                    "status": status,
                    "due_date": due_date,
                    "requested_date": None,
                    "related_link": related_link,
                    "needs_confirmation": needs_confirmation,
                },
            )
        st.success("タスクを作成しました。")
        st.rerun()

st.subheader("タスク編集 / 状態変更")
with service_scope() as container:
    task_options = container.task_service.task_options(include_requests=False)
selected = st.selectbox("編集対象", options=task_options, format_func=lambda x: x["label"] if x else "", index=None)

if selected:
    with service_scope() as container:
        detail = container.task_service.get_task_detail(selected["value"])

    st.caption(f'依頼元: {detail["requester_name"]} / 現在の担当者: {detail["assignee_name"]}')
    with st.form("edit_task_form"):
        title = st.text_input("件名", value=detail["title"])
        description = st.text_area("内容", value=detail["description"] or "")
        c1, c2, c3, c4 = st.columns(4)
        status = c1.selectbox("ステータス", STATUSES, index=STATUSES.index(detail["status"]))
        priority = c2.selectbox("優先度", PRIORITIES, index=PRIORITIES.index(detail["priority"]))
        due_date = c3.date_input("期限日", value=detail["due_date"])
        assignee = c4.selectbox(
            "担当者",
            options=user_options,
            index=next((idx for idx, item in enumerate(user_options) if item["value"] == detail["assignee_user_id"]), 0),
            format_func=lambda x: x["label"],
        )
        related_link = st.text_input("関連リンク", value=detail["related_link"] or "")
        update = st.form_submit_button("更新", use_container_width=True)
        if update:
            with service_scope() as container:
                container.task_service.update_task(
                    task_id=selected["value"],
                    actor_id=user["user_id"],
                    payload={
                        "title": title,
                        "description": description,
                        "status": status,
                        "priority": priority,
                        "due_date": due_date,
                        "assignee_user_id": assignee["value"],
                        "related_link": related_link,
                    },
                )
            st.success("タスクを更新しました。")
            st.rerun()

    a1, a2, a3, a4 = st.columns(4)
    if a1.button("未着手", use_container_width=True):
        with service_scope() as container:
            container.task_service.change_status(selected["value"], "未着手", user["user_id"])
        st.rerun()
    if a2.button("進行中", use_container_width=True):
        with service_scope() as container:
            container.task_service.change_status(selected["value"], "進行中", user["user_id"])
        st.rerun()
    if a3.button("保留", use_container_width=True):
        with service_scope() as container:
            container.task_service.change_status(selected["value"], "保留", user["user_id"])
        st.rerun()
    if a4.button("完了", use_container_width=True):
        with service_scope() as container:
            container.task_service.change_status(selected["value"], "完了", user["user_id"])
        st.rerun()

    st.markdown("#### コメント")
    with service_scope() as container:
        comments = container.task_service.get_comments_display(selected["value"])
    st.dataframe(comments, use_container_width=True, hide_index=True)
    comment = st.text_area("コメント内容")
    if st.button("コメント追加", use_container_width=True) and comment:
        with service_scope() as container:
            container.task_service.add_comment(selected["value"], user["user_id"], comment)
        st.rerun()
