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
    "SV依頼": "#FF5A5F",
    "定期": "#5E5CE6",
}
PRIORITY_COLORS = {"高": "#FF5A5F", "中": "#FF9F0A", "低": "#8E8E93"}
STATUS_COLORS = {
    "未着手": "#8E8E93",
    "確認待ち": "#FF9F0A",
    "進行中": "#4F8CFF",
    "保留": "#6E56CF",
    "完了": "#34C759",
    "取消": "#7D7D84",
}


def badge(label: str, color: str, filled: bool = True) -> str:
    if filled:
        style = f"background:{color};color:#ffffff;border:1px solid {color};"
    else:
        style = f"background:#ffffff;color:{color};border:1px solid {color};"
    return (
        f"<span style='display:inline-block;padding:0.12rem 0.5rem;margin-right:0.28rem;"
        f"border-radius:999px;font-size:0.76rem;font-weight:700;{style}'>{label}</span>"
    )


def format_due_date(value) -> str:
    return value.strftime("%Y-%m-%d") if value else "期限未設定"


def build_summary(tasks: list[dict]) -> dict:
    today = date.today()
    return {
        "未着手": sum(1 for task in tasks if task["status"] == "未着手"),
        "今日期限": sum(1 for task in tasks if task["due_date"] == today),
        "期限超過": sum(
            1
            for task in tasks
            if task["due_date"] and task["due_date"] < today and task["status"] != "完了"
        ),
        "要確認": sum(1 for task in tasks if task["needs_confirmation"]),
    }


def summary_card(title: str, value: int, tone: str):
    with st.container(border=True):
        st.caption(title)
        st.metric(title, value, label_visibility="collapsed")


def render_task_card(task: dict, is_editing: bool):
    overdue = task["due_date"] and task["due_date"] < date.today() and task["status"] != "完了"
    title_prefix = "編集中: " if is_editing else ""

    card_cols = st.columns([0.18, 5.5, 0.9, 0.9], gap="small")
    with card_cols[0]:
        st.markdown(
            f"<div style='background:{task['project_color']};width:8px;height:72px;border-radius:999px;margin-top:0.1rem;'></div>",
            unsafe_allow_html=True,
        )
    with card_cols[1]:
        st.markdown(f"**{title_prefix}{task['title']}**")
        st.markdown(
            " ".join(
                [
                    badge(task["project_name"], task["project_color"], filled=False),
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
        if task["needs_confirmation"]:
            st.markdown(badge("要確認", "#D9363E"), unsafe_allow_html=True)
    with card_cols[2]:
        if st.button("編集", key=f"edit_{task['task_id']}", use_container_width=True):
            st.session_state["editing_task_id"] = task["task_id"]
            st.session_state["show_task_create"] = False
            st.rerun()
    with card_cols[3]:
        done_disabled = task["status"] == "完了"
        if st.button("完了", key=f"done_{task['task_id']}", use_container_width=True, disabled=done_disabled):
            with service_scope() as container:
                container.task_service.change_status(task["task_id"], "完了", st.session_state["current_user"]["user_id"])
            st.rerun()


st.set_page_config(page_title="タスク", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("タスク")
st.caption("一覧を見ながら、そのまま右側で更新できる業務向けタスク画面です。")

with service_scope() as container:
    user_options = container.master_service.user_options()
    team_options = container.master_service.team_options()
    project_options = container.master_service.project_options()

with st.container(border=True):
    st.markdown("#### 絞り込み")
    f1, f2, f3, f4 = st.columns(4)
    filters = {
        "mine_only": f1.checkbox("自分のタスクのみ", value=True),
        "today_due": f2.checkbox("今日期限"),
        "overdue_only": f3.checkbox("期限超過のみ"),
        "exclude_completed": f4.checkbox("完了を除外", value=True),
    }

with service_scope() as container:
    tasks = container.task_service.list_tasks_for_display(user["user_id"], filters)

summary = build_summary(tasks)
sum_cols = st.columns(4)
with sum_cols[0]:
    summary_card("未着手", summary["未着手"], "neutral")
with sum_cols[1]:
    summary_card("今日期限", summary["今日期限"], "info")
with sum_cols[2]:
    summary_card("期限超過", summary["期限超過"], "danger")
with sum_cols[3]:
    summary_card("要確認", summary["要確認"], "warn")

list_col, panel_col = st.columns([1.45, 1], gap="large")

with list_col:
    header_cols = st.columns([1.1, 0.7])
    header_cols[0].subheader("タスク一覧")
    if header_cols[1].button("+ 新規作成", use_container_width=True, type="primary"):
        st.session_state["show_task_create"] = not st.session_state.get("show_task_create", False)
        st.session_state.pop("editing_task_id", None)
        st.rerun()

    if not tasks:
        st.info("表示対象のタスクはありません。")

    for task in tasks:
        with st.container(border=True):
            render_task_card(task, st.session_state.get("editing_task_id") == task["task_id"])

with panel_col:
    editing_task_id = st.session_state.get("editing_task_id")

    if st.session_state.get("show_task_create", False):
        st.info("新規作成パネル")
        with st.container(border=True):
            with st.form("create_task_form", clear_on_submit=True):
                c1, c2 = st.columns([1.2, 0.8])
                c1.markdown("### 新規タスク")
                cancel_create = c2.form_submit_button("キャンセル", use_container_width=True)
                title = st.text_input("件名")
                description = st.text_area("内容", height=110)

                g1, g2, g3, g4 = st.columns(4)
                task_type = g1.selectbox("種別", options=TASK_TYPES, format_func=lambda x: x[1])
                priority = g2.selectbox("優先度", PRIORITIES)
                status = g3.selectbox("状態", STATUSES, index=0)
                assignee = g4.selectbox("担当者", options=user_options, format_func=lambda x: x["label"])

                g5, g6, g7 = st.columns(3)
                team = g5.selectbox("チーム", options=team_options, format_func=lambda x: x["label"])
                if project_options:
                    project = g6.selectbox("プロジェクト", options=project_options, format_func=lambda x: x["label"])
                else:
                    project = None
                    g6.caption("有効なプロジェクトがありません")
                due_date = g7.date_input("期限", value=None)

                g8, g9 = st.columns([3, 1])
                related_link = g8.text_input("関連リンク")
                needs_confirmation = g9.checkbox("要確認")

                save_create = st.form_submit_button("保存", use_container_width=True, type="primary")

                if cancel_create:
                    st.session_state["show_task_create"] = False
                    st.rerun()

                if save_create:
                    if not title.strip():
                        st.warning("件名を入力してください。")
                    elif not project:
                        st.warning("有効なプロジェクトを選択してください。")
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
                action_cols = st.columns(3)
                save_clicked = action_cols[0].form_submit_button("保存", use_container_width=True, type="primary")
                complete_clicked = action_cols[1].form_submit_button("完了", use_container_width=True)
                cancel_clicked = action_cols[2].form_submit_button("キャンセル", use_container_width=True)

                title = st.text_input("件名", value=detail["title"])
                description = st.text_area("内容", value=detail["description"] or "", height=110)

                g1, g2, g3, g4 = st.columns(4)
                task_type = g1.selectbox(
                    "種別",
                    options=TASK_TYPES,
                    index=next((idx for idx, item in enumerate(TASK_TYPES) if item[0] == detail["task_type"]), 0),
                    format_func=lambda x: x[1],
                )
                priority = g2.selectbox("優先度", PRIORITIES, index=PRIORITIES.index(detail["priority"]))
                status = g3.selectbox("状態", STATUSES, index=STATUSES.index(detail["status"]))
                assignee = g4.selectbox(
                    "担当者",
                    options=user_options,
                    index=next((idx for idx, item in enumerate(user_options) if item["value"] == detail["assignee_user_id"]), 0),
                    format_func=lambda x: x["label"],
                )

                g5, g6, g7 = st.columns(3)
                team = g5.selectbox(
                    "チーム",
                    options=team_options,
                    index=next((idx for idx, item in enumerate(team_options) if item["value"] == detail["team_id"]), 0),
                    format_func=lambda x: x["label"],
                )
                project = g6.selectbox(
                    "プロジェクト",
                    options=project_options,
                    index=next((idx for idx, item in enumerate(project_options) if item["value"] == detail["project_id"]), 0),
                    format_func=lambda x: x["label"],
                )
                due_date = g7.date_input("期限", value=detail["due_date"])

                g8, g9 = st.columns([3, 1])
                related_link = g8.text_input("関連リンク", value=detail["related_link"] or "")
                needs_confirmation = g9.checkbox("要確認", value=detail["needs_confirmation"])

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
        if st.button("コメントを保存", key="add_task_comment", use_container_width=True):
            if comment.strip():
                with service_scope() as container:
                    container.task_service.add_comment(editing_task_id, user["user_id"], comment.strip())
                st.rerun()
            else:
                st.warning("コメントを入力してください。")

    else:
        with st.container(border=True):
            st.subheader("操作パネル")
            st.caption("左のカードから編集を選ぶか、上の「+ 新規作成」で新しいタスクを追加してください。")
