from datetime import date

import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar


TASK_TYPES = [
    ("personal_task", "個人"),
    ("team_task", "チーム"),
    ("handover_task", "引継ぎ"),
    ("sv_request", "SV依頼"),
    ("recurring_task", "定期"),
]
STATUSES = ["未着手", "確認待ち", "進行中", "保留", "完了", "取消"]
PRIORITIES = ["高", "中", "低"]

TYPE_COLORS = {
    "個人": "#4F8CFF",
    "チーム": "#34C759",
    "引継ぎ": "#8E8E93",
    "SV依頼": "#64748B",
    "定期": "#5E5CE6",
}
PRIORITY_COLORS = {"高": "#FF5A5F", "中": "#FF9F0A", "低": "#8E8E93"}
STATUS_COLORS = {
    "未着手": "#8E8E93",
    "確認待ち": "#FF9F0A",
    "進行中": "#4F8CFF",
    "保留": "#6E56CF",
    "完了": "#16A34A",
    "取消": "#DC2626",
}


def badge(label: str, color: str, filled: bool = True) -> str:
    if filled:
        style = f"background:{color};color:#ffffff;border:1px solid {color};"
    else:
        style = f"background:#ffffff;color:{color};border:1px solid {color};"
    return (
        f"<span style='display:inline-block;padding:0.12rem 0.5rem;margin-right:0.25rem;"
        f"border-radius:999px;font-size:0.76rem;font-weight:700;{style}'>{label}</span>"
    )


def project_chip(color: str) -> str:
    return (
        f"<span style='display:inline-block;width:12px;height:12px;border-radius:999px;"
        f"background:{color};border:1px solid rgba(0,0,0,0.15);margin-right:0.4rem;vertical-align:middle;'></span>"
    )


def format_due_date(value) -> str:
    return value.strftime("%Y-%m-%d") if value else "期限未設定"


def build_summary(tasks: list[dict]) -> dict:
    today = date.today()
    return {
        "未着手": sum(1 for task in tasks if task["status"] == "未着手"),
        "今日期限": sum(1 for task in tasks if task["due_date"] == today),
        "期限超過": sum(
            1 for task in tasks if task["due_date"] and task["due_date"] < today and task["status"] not in {"完了", "取消"}
        ),
        "要確認": sum(1 for task in tasks if task["needs_confirmation"]),
    }


def render_summary_card(title: str, value: int):
    with st.container(border=True):
        st.caption(title)
        st.metric(title, value, label_visibility="collapsed")


def render_task_card(task: dict, actor_id: int):
    is_editing = st.session_state.get("editing_task_id") == task["task_id"]
    overdue = task["due_date"] and task["due_date"] < date.today() and task["status"] not in {"完了", "取消"}

    info_col, action_col = st.columns([4, 1], gap="medium")

    with info_col:
        title_left, title_right = st.columns([8, 1], gap="small")
        with title_left:
            title_html = (
                f"{project_chip(task['project_color'])}"
                f"<span style='font-weight:700;font-size:1rem;color:#111827;'>{task['title']}</span>"
            )
            st.markdown(title_html, unsafe_allow_html=True)
        with title_right:
            if task["needs_confirmation"]:
                st.markdown(
                    "<div style='text-align:right;font-size:1rem;color:#DC2626;font-weight:700;'>⚠ 要確認</div>",
                    unsafe_allow_html=True,
                )
            elif is_editing:
                st.caption("編集中")

        st.markdown(
            " ".join(
                [
                    badge(task["task_type_label"], TYPE_COLORS.get(task["task_type_label"], "#8E8E93")),
                    badge(task["priority"], PRIORITY_COLORS.get(task["priority"], "#8E8E93")),
                    badge(task["status"], STATUS_COLORS.get(task["status"], "#8E8E93")),
                ]
            ),
            unsafe_allow_html=True,
        )

        meta = [
            f"依頼元: {task['requester_name']}",
            f"担当: {task['assignee_name']}",
            f"期限: {format_due_date(task['due_date'])}",
        ]
        if overdue:
            meta.append("期限超過")
        st.caption(" / ".join(meta))

    with action_col:
        if st.button("編集", key=f"edit_{task['task_id']}", use_container_width=True):
            st.session_state["editing_task_id"] = task["task_id"]
            st.session_state["show_task_create"] = False
            st.rerun()

        st.markdown("<div class='success-button-marker'></div>", unsafe_allow_html=True)
        if st.button(
            "完了",
            key=f"done_{task['task_id']}",
            disabled=task["status"] == "完了",
            use_container_width=True,
        ):
            with service_scope() as container:
                container.task_service.change_status(task["task_id"], "完了", actor_id)
            st.rerun()

        st.markdown("<div class='danger-button-marker'></div>", unsafe_allow_html=True)
        if st.button(
            "取消",
            key=f"archive_{task['task_id']}",
            disabled=task["status"] == "取消",
            use_container_width=True,
        ):
            with service_scope() as container:
                container.task_service.archive_task(task["task_id"], actor_id)
            if st.session_state.get("editing_task_id") == task["task_id"]:
                st.session_state.pop("editing_task_id", None)
            st.rerun()


st.set_page_config(page_title="タスク", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("タスク")
st.caption("一覧を見ながら編集しやすい運用向けUIです。")

with service_scope() as container:
    user_options = container.master_service.user_options()
    team_options = container.master_service.team_options()
    project_options = container.master_service.project_options()

with st.container(border=True):
    st.markdown("#### 絞り込み")
    f1, f2, f3, f4, f5 = st.columns(5)
    filters = {
        "mine_only": f1.checkbox("自分のタスクのみ", value=True),
        "today_due": f2.checkbox("今日期限"),
        "overdue_only": f3.checkbox("期限超過のみ"),
        "exclude_completed": f4.checkbox("完了を除外", value=True),
        "show_archived": f5.checkbox("取消済みを表示"),
    }

with service_scope() as container:
    tasks = container.task_service.list_tasks_for_display(user["user_id"], filters)

summary = build_summary(tasks)
sum_cols = st.columns(4)
with sum_cols[0]:
    render_summary_card("未着手", summary["未着手"])
with sum_cols[1]:
    render_summary_card("今日期限", summary["今日期限"])
with sum_cols[2]:
    render_summary_card("期限超過", summary["期限超過"])
with sum_cols[3]:
    render_summary_card("要確認", summary["要確認"])

has_panel = st.session_state.get("show_task_create", False) or bool(st.session_state.get("editing_task_id"))
if has_panel:
    list_col, panel_col = st.columns([1.45, 1], gap="large")
else:
    list_col = st.container()
    panel_col = None

with list_col:
    head_col, action_head_col = st.columns([8, 2], gap="small")
    with head_col:
        st.subheader("タスク一覧")
    with action_head_col:
        if st.button("+ 新規作成", type="primary", use_container_width=True):
            st.session_state["show_task_create"] = True
            st.session_state.pop("editing_task_id", None)
            st.rerun()

    if not tasks:
        st.info("表示対象のタスクはありません。")

    for task in tasks:
        with st.container(border=True):
            render_task_card(task, user["user_id"])

if panel_col:
    with panel_col:
        editing_task_id = st.session_state.get("editing_task_id")

        if st.session_state.get("show_task_create", False):
            st.info("新規作成モード")
            with st.container(border=True):
                with st.form("create_task_form", clear_on_submit=True):
                    top = st.columns([1.4, 0.8])
                    top[0].markdown("### 新規タスク")
                    close_create = top[1].form_submit_button("閉じる")

                    title = st.text_input("件名")
                    description = st.text_area("内容", height=110)

                    r1 = st.columns(4)
                    task_type = r1[0].selectbox("種別", options=TASK_TYPES, format_func=lambda x: x[1])
                    priority = r1[1].selectbox("優先度", PRIORITIES)
                    status = r1[2].selectbox("状態", STATUSES, index=0)
                    assignee = r1[3].selectbox("担当者", options=user_options, format_func=lambda x: x["label"])

                    r2 = st.columns(3)
                    team = r2[0].selectbox("チーム", options=team_options, format_func=lambda x: x["label"])
                    project = r2[1].selectbox("プロジェクト", options=project_options, format_func=lambda x: x["label"])
                    due_date = r2[2].date_input("期限", value=None)

                    r3 = st.columns([3, 1])
                    related_link = r3[0].text_input("関連リンク")
                    needs_confirmation = r3[1].checkbox("要確認")

                    save_create = st.form_submit_button("保存", type="primary")

                    if close_create:
                        st.session_state["show_task_create"] = False
                        st.rerun()
                    if save_create:
                        if not title.strip():
                            st.warning("件名を入力してください。")
                        else:
                            with service_scope() as container:
                                container.task_service.create_task(
                                    actor_id=user["user_id"],
                                    payload={
                                        "task_type": task_type[0],
                                        "title": title.strip(),
                                        "description": description.strip(),
                                        "requester_user_id": user["user_id"],
                                        "assignee_user_id": assignee["value"],
                                        "team_id": team["value"],
                                        "project_id": project["value"],
                                        "priority": priority,
                                        "status": status,
                                        "due_date": due_date,
                                        "requested_date": None,
                                        "related_link": related_link.strip(),
                                        "needs_confirmation": needs_confirmation,
                                    },
                                )
                            st.session_state["show_task_create"] = False
                            st.success("タスクを登録しました。")
                            st.rerun()

        elif editing_task_id:
            with service_scope() as container:
                detail = container.task_service.get_task_detail(editing_task_id)

            current_project = next(
                (item for item in project_options if item["value"] == detail["project_id"]),
                {"label": "未設定", "color": "#8E8E93", "value": detail["project_id"]},
            )
            st.info("編集モード")
            st.markdown(
                " ".join(
                    [
                        badge("編集中", current_project["color"], filled=False),
                        badge(current_project["label"], current_project["color"], filled=False),
                    ]
                ),
                unsafe_allow_html=True,
            )
            st.markdown(f"### 現在編集中: {detail['title']}")
            st.caption(f"依頼元: {detail['requester_name']} / 担当: {detail['assignee_name']}")

            with st.container(border=True):
                with st.form("edit_task_form"):
                    action = st.columns(3)
                    save_clicked = action[0].form_submit_button("保存", type="primary")
                    complete_clicked = action[1].form_submit_button("完了")
                    cancel_clicked = action[2].form_submit_button("キャンセル")

                    title = st.text_input("件名", value=detail["title"])
                    description = st.text_area("内容", value=detail["description"] or "", height=110)

                    r1 = st.columns(4)
                    task_type = r1[0].selectbox(
                        "種別",
                        options=TASK_TYPES,
                        index=next((idx for idx, item in enumerate(TASK_TYPES) if item[0] == detail["task_type"]), 0),
                        format_func=lambda x: x[1],
                    )
                    priority = r1[1].selectbox("優先度", PRIORITIES, index=PRIORITIES.index(detail["priority"]))
                    status = r1[2].selectbox("状態", STATUSES, index=STATUSES.index(detail["status"]))
                    assignee = r1[3].selectbox(
                        "担当者",
                        options=user_options,
                        index=next((idx for idx, item in enumerate(user_options) if item["value"] == detail["assignee_user_id"]), 0),
                        format_func=lambda x: x["label"],
                    )

                    r2 = st.columns(3)
                    team = r2[0].selectbox(
                        "チーム",
                        options=team_options,
                        index=next((idx for idx, item in enumerate(team_options) if item["value"] == detail["team_id"]), 0),
                        format_func=lambda x: x["label"],
                    )
                    project = r2[1].selectbox(
                        "プロジェクト",
                        options=project_options,
                        index=next((idx for idx, item in enumerate(project_options) if item["value"] == detail["project_id"]), 0),
                        format_func=lambda x: x["label"],
                    )
                    due_date = r2[2].date_input("期限", value=detail["due_date"])

                    r3 = st.columns([3, 1])
                    related_link = r3[0].text_input("関連リンク", value=detail["related_link"] or "")
                    needs_confirmation = r3[1].checkbox("要確認", value=detail["needs_confirmation"])

                    if cancel_clicked:
                        st.session_state.pop("editing_task_id", None)
                        st.rerun()
                    if complete_clicked:
                        with service_scope() as container:
                            container.task_service.change_status(editing_task_id, "完了", user["user_id"])
                        st.success("タスクを完了にしました。")
                        st.rerun()
                    if save_clicked:
                        with service_scope() as container:
                            container.task_service.update_task(
                                task_id=editing_task_id,
                                actor_id=user["user_id"],
                                payload={
                                    "task_type": task_type[0],
                                    "title": title.strip(),
                                    "description": description.strip(),
                                    "status": status,
                                    "priority": priority,
                                    "assignee_user_id": assignee["value"],
                                    "team_id": team["value"],
                                    "project_id": project["value"],
                                    "due_date": due_date,
                                    "related_link": related_link.strip(),
                                    "needs_confirmation": needs_confirmation,
                                },
                            )
                        st.success("タスクを更新しました。")
                        st.rerun()

            st.markdown("#### コメント")
            with service_scope() as container:
                comments = container.task_service.get_comments_display(editing_task_id)
            if comments:
                st.dataframe(comments, use_container_width=True, hide_index=True)
            else:
                st.caption("コメントはまだありません。")

            comment = st.text_area("コメント追加", height=90)
            if st.button("コメントを保存"):
                if comment.strip():
                    with service_scope() as container:
                        container.task_service.add_comment(editing_task_id, user["user_id"], comment.strip())
                    st.rerun()
                else:
                    st.warning("コメントを入力してください。")
