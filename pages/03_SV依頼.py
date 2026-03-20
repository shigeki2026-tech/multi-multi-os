import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar


PRIORITIES = ["高", "中", "低"]

st.set_page_config(page_title="SV依頼", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("SV依頼")

with service_scope() as container:
    user_options = container.master_service.user_options()
    team_options = container.master_service.team_options()
    project_options = container.master_service.project_options()

with st.form("create_request_form", clear_on_submit=True):
    title = st.text_input("件名")
    description = st.text_area("内容")
    c1, c2, c3, c4 = st.columns(4)
    assignee = c1.selectbox("担当者", options=user_options, format_func=lambda x: x["label"])
    team = c2.selectbox("関連チーム", options=team_options, format_func=lambda x: x["label"])
    project = c3.selectbox("関連プロジェクト", options=project_options, format_func=lambda x: x["label"])
    priority = c4.selectbox("優先度", PRIORITIES)
    c5, c6, c7 = st.columns(3)
    requested_date = c5.date_input("依頼日")
    due_date = c6.date_input("期限", value=None)
    needs_confirmation = c7.checkbox("要確認", value=True)
    related_link = st.text_input("関連リンク")
    submit = st.form_submit_button("依頼を作成", type="primary")
    if submit and title:
        with service_scope() as container:
            container.request_service.create_request(
                actor_id=user["user_id"],
                payload={
                    "title": title,
                    "description": description,
                    "requester_user_id": user["user_id"],
                    "assignee_user_id": assignee["value"],
                    "team_id": team["value"],
                    "project_id": project["value"],
                    "priority": priority,
                    "requested_date": requested_date,
                    "due_date": due_date,
                    "status": "確認待ち",
                    "related_link": related_link,
                    "needs_confirmation": needs_confirmation,
                },
            )
        st.success("依頼を作成しました。")
        st.rerun()

with service_scope() as container:
    sent = container.request_service.list_sent_for_display(user["user_id"])
    request_options = container.request_service.request_options()

left, right = st.columns(2)
with left:
    st.subheader("自分が受けた依頼")
    only_unack = st.checkbox("未確認のみ表示", value=False)
    with service_scope() as container:
        received = container.request_service.list_received_for_display(user["user_id"], only_unack)
    st.dataframe(received, use_container_width=True, hide_index=True)

with right:
    st.subheader("自分が出した依頼")
    st.dataframe(sent, use_container_width=True, hide_index=True)

selected = st.selectbox(
    "操作対象の依頼",
    options=request_options,
    format_func=lambda x: x["label"] if x else "",
    index=None,
    placeholder="依頼を選択",
)
if selected:
    with service_scope() as container:
        detail = container.request_service.get_request_detail(selected["value"])
        comments = container.request_service.get_comments_display(selected["value"])
    st.markdown("#### 依頼詳細")
    st.json(detail)

    b1, b2, b3, b4 = st.columns(4)
    if b1.button("確認した"):
        with service_scope() as container:
            container.request_service.acknowledge_request(selected["value"], user["user_id"])
        st.rerun()
    if b2.button("進行中"):
        with service_scope() as container:
            container.request_service.change_status(selected["value"], "進行中", user["user_id"])
        st.rerun()
    if b3.button("保留"):
        with service_scope() as container:
            container.request_service.change_status(selected["value"], "保留", user["user_id"])
        st.rerun()
    if b4.button("完了"):
        with service_scope() as container:
            container.request_service.change_status(selected["value"], "完了", user["user_id"])
        st.rerun()

    st.markdown("#### コメント履歴")
    st.dataframe(comments, use_container_width=True, hide_index=True)
    comment = st.text_area("コメント追加", key=f"req_comment_{selected['value']}")
    if st.button("コメントを保存") and comment:
        with service_scope() as container:
            container.request_service.add_comment(selected["value"], user["user_id"], comment)
        st.rerun()
