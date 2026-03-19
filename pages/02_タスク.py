from datetime import date

import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in


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
    "個人": "#3559E0",
    "チーム": "#0F9D58",
    "引継ぎ": "#7B61FF",
    "SV依頼": "#D9485F",
    "定期": "#6C757D",
}
PRIORITY_COLORS = {"高": "#D9485F", "中": "#F08C00", "低": "#868E96"}
STATUS_COLORS = {
    "未着手": "#6C757D",
    "確認待ち": "#F08C00",
    "進行中": "#1C7ED6",
    "保留": "#7950F2",
    "完了": "#2B8A3E",
    "取消": "#495057",
}
CONFIRM_COLOR = "#C92A2A"


def badge(label: str, color: str, outlined: bool = False) -> str:
    if outlined:
        return (
            f"<span style='display:inline-block;padding:0.12rem 0.5rem;border-radius:999px;"
            f"border:1px solid {color};color:{color};font-size:0.76rem;font-weight:700;"
            f"background:#ffffff;'>{label}</span>"
        )
    return (
        f"<span style='display:inline-block;padding:0.12rem 0.5rem;border-radius:999px;"
        f"background:{color};color:#ffffff;font-size:0.76rem;font-weight:700;'>{label}</span>"
    )


def format_due_date(value) -> str:
    return value.strftime("%Y-%m-%d") if value else "-"


def render_summary_card(title: str, value: int, tone: str):
    colors = {
        "neutral": ("#F6F7FB", "#425466"),
        "info": ("#EEF6FF", "#1C7ED6"),
        "danger": ("#FFF1F3", "#C92A2A"),
        "warn": ("#FFF4E6", "#E67700"),
    }
    background, text_color = colors[tone]
    st.markdown(
        f"""
        <div style="background:{background};border:1px solid rgba(0,0,0,0.05);border-radius:14px;
        padding:0.8rem 0.95rem;min-height:88px;">
            <div style="font-size:0.82rem;color:#667085;font-weight:600;">{title}</div>
            <div style="font-size:1.7rem;color:{text_color};font-weight:800;line-height:1.2;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_task_summary(tasks: list[dict]) -> dict:
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


def render_task_row(task: dict, is_editing: bool):
    accent = task.get("project_color") or "#5B6CFF"
    background = "#F8FAFF" if is_editing else "#FFFFFF"
    border = "#C7D2FE" if is_editing else "#E9EDF5"
    editing_text = (
        "<div style='font-size:0.72rem;color:#3559E0;font-weight:700;margin-bottom:0.18rem;'>現在編集中</div>"
        if is_editing
        else ""
    )
    confirm_badge = (
        f"&nbsp;{badge('要確認', CONFIRM_COLOR)}" if task["needs_confirmation"] else ""
    )
    meta_html = " ".join(
        [
            badge(task["project_name"], accent, outlined=True),
            badge(task["task_type_label"], TYPE_COLORS.get(task["task_type_label"], "#6C757D")),
            badge(task["priority"], PRIORITY_COLORS.get(task["priority"], "#6C757D")),
            badge(task["status"], STATUS_COLORS.get(task["status"], "#6C757D")),
        ]
    )
    subline = (
        f"依頼元: {task['requester_name']}　/　担当: {task['assignee_name']}　/　期限: {format_due_date(task['due_date'])}"
    )
    st.markdown(
        f"""
        <div style="border-left:5px solid {accent};background:{background};border:1px solid {border};
        border-radius:14px;padding:0.58rem 0.8rem 0.56rem 0.82rem;">
            {editing_text}
            <div style="font-size:0.98rem;font-weight:800;color:#1F2937;line-height:1.3;margin-bottom:0.3rem;">
                {task["title"]}{confirm_badge}
            </div>
            <div style="margin-bottom:0.34rem;">{meta_html}</div>
            <div style="font-size:0.8rem;color:#667085;line-height:1.35;">{subline}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="タスク", layout="wide")
ensure_app_ready()
user = ensure_logged_in()

st.title("タスク")
st.caption("一覧性を優先した業務向けタスク管理")

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

summary = build_task_summary(tasks)
summary_cols = st.columns(4)
with summary_cols[0]:
    render_summary_card("未着手", summary["未着手"], "neutral")
with summary_cols[1]:
    render_summary_card("今日期限", summary["今日期限"], "info")
with summary_cols[2]:
    render_summary_card("期限超過", summary["期限超過"], "danger")
with summary_cols[3]:
    render_summary_card("要確認", summary["要確認"], "warn")

left, right = st.columns([1.45, 1], gap="large")

with left:
    top_cols = st.columns([1.2, 0.8])
    top_cols[0].subheader("タスク一覧")
    if top_cols[1].button("+ 新規作成", use_container_width=True):
        st.session_state["show_task_create"] = not st.session_state.get("show_task_create", False)
        st.session_state.pop("editing_task_id", None)
        st.rerun()

    if not tasks:
        st.info("表示対象のタスクはありません。")

    for task in tasks:
        row_cols = st.columns([6.2, 1.1], gap="small")
        with row_cols[0]:
            render_task_row(task, st.session_state.get("editing_task_id") == task["task_id"])
        with row_cols[1]:
            st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)
            if st.button("編集", key=f"edit_task_{task['task_id']}", use_container_width=True):
                st.session_state["editing_task_id"] = task["task_id"]
                st.session_state["show_task_create"] = False
                st.rerun()

with right:
    panel_accent = "#3559E0"
    editing_task_id = st.session_state.get("editing_task_id")

    if st.session_state.get("show_task_create", False):
        st.markdown(
            f"""
            <div style="border-left:5px solid {panel_accent};padding:0.2rem 0 0.7rem 0.9rem;
            margin-bottom:0.8rem;background:#F8FAFF;border-radius:12px;">
                <div style="font-size:1.05rem;font-weight:800;">新規作成</div>
                <div style="font-size:0.82rem;color:#667085;">必要な項目だけをまとめて登録します。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            with st.form("create_task_form", clear_on_submit=True):
                title = st.text_input("件名")
                description = st.text_area("内容", height=110)

                c1, c2, c3, c4 = st.columns(4)
                task_type = c1.selectbox("種別", options=TASK_TYPES, format_func=lambda x: x[1])
                priority = c2.selectbox("優先度", PRIORITIES)
                status = c3.selectbox("状態", STATUSES, index=0)
                assignee = c4.selectbox("担当者", options=user_options, format_func=lambda x: x["label"])

                c5, c6, c7 = st.columns(3)
                team = c5.selectbox("チーム", options=team_options, format_func=lambda x: x["label"])
                if project_options:
                    project = c6.selectbox(
                        "プロジェクト",
                        options=project_options,
                        format_func=lambda x: x["label"],
                    )
                else:
                    project = None
                    c6.caption("有効なプロジェクトがありません")
                due_date = c7.date_input("期限", value=None)

                c8, c9 = st.columns([3, 1])
                related_link = c8.text_input("関連リンク")
                needs_confirmation = c9.checkbox("要確認")

                submit = st.form_submit_button("登録する", use_container_width=True)
                if submit:
                    if not title.strip():
                        st.warning("件名を入力してください。")
                    elif not project_options:
                        st.warning("有効なプロジェクトがありません。管理画面で追加してください。")
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

        accent = next(
            (item["color"] for item in project_options if item["value"] == detail["project_id"]),
            "#3559E0",
        )
        st.markdown(
            f"""
            <div style="border-left:5px solid {accent};padding:0.25rem 0 0.7rem 0.9rem;
            margin-bottom:0.8rem;background:#F8FAFF;border-radius:12px;">
                <div style="font-size:0.82rem;color:#3559E0;font-weight:700;">現在編集中</div>
                <div style="font-size:1.05rem;font-weight:800;">{detail["title"]}</div>
                <div style="font-size:0.82rem;color:#667085;">
                    依頼元: {detail["requester_name"]} / 担当: {detail["assignee_name"]} / 種別: {detail["task_type_label"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            with st.form("edit_task_form"):
                title = st.text_input("件名", value=detail["title"])
                description = st.text_area("内容", value=detail["description"] or "", height=110)

                c1, c2, c3, c4 = st.columns(4)
                task_type = c1.selectbox(
                    "種別",
                    options=TASK_TYPES,
                    index=next((idx for idx, item in enumerate(TASK_TYPES) if item[0] == detail["task_type"]), 0),
                    format_func=lambda x: x[1],
                )
                priority = c2.selectbox("優先度", PRIORITIES, index=PRIORITIES.index(detail["priority"]))
                status = c3.selectbox("状態", STATUSES, index=STATUSES.index(detail["status"]))
                assignee = c4.selectbox(
                    "担当者",
                    options=user_options,
                    index=next((idx for idx, item in enumerate(user_options) if item["value"] == detail["assignee_user_id"]), 0),
                    format_func=lambda x: x["label"],
                )

                c5, c6, c7 = st.columns(3)
                team = c5.selectbox(
                    "チーム",
                    options=team_options,
                    index=next((idx for idx, item in enumerate(team_options) if item["value"] == detail["team_id"]), 0),
                    format_func=lambda x: x["label"],
                )
                project = c6.selectbox(
                    "プロジェクト",
                    options=project_options,
                    index=next((idx for idx, item in enumerate(project_options) if item["value"] == detail["project_id"]), 0),
                    format_func=lambda x: x["label"],
                )
                due_date = c7.date_input("期限", value=detail["due_date"])

                c8, c9 = st.columns([3, 1])
                related_link = c8.text_input("関連リンク", value=detail["related_link"] or "")
                needs_confirmation = c9.checkbox("要確認", value=detail["needs_confirmation"])

                update = st.form_submit_button("変更を保存", use_container_width=True)
                if update:
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

            action_cols = st.columns(5)
            actions = [("未着手", "未着手"), ("進行中", "進行中"), ("保留", "保留"), ("完了", "完了")]
            for idx, (label, status) in enumerate(actions):
                if action_cols[idx].button(label, key=f"quick_status_{status}", use_container_width=True):
                    with service_scope() as container:
                        container.task_service.change_status(editing_task_id, status, user["user_id"])
                    st.rerun()
            if action_cols[4].button("編集を閉じる", use_container_width=True):
                st.session_state.pop("editing_task_id", None)
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
            st.subheader("編集パネル")
            st.caption("左の一覧から「編集」を押すか、「+ 新規作成」で新しいタスクを登録してください。")
