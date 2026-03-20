import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar


st.set_page_config(page_title="応答率速報", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

with service_scope() as container:
    project_options = container.master_service.project_options()
    history = container.leoc_service.list_history_for_display()

st.title("応答率速報")
st.caption("案件ごとの応答率速報を手入力で集計します。将来は呼詳細などからの自動集計へ拡張する前提です。")

project = st.selectbox("案件選択", options=project_options, format_func=lambda x: x["label"])

with st.form("response_snapshot_form"):
    c1, c2 = st.columns(2)
    snapshot_time = c1.selectbox(
        "時点",
        ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"],
    )
    lost_count = c2.number_input("呼損件数", min_value=0, step=1, value=0)
    creators_text = st.text_area(
        "作成者一覧",
        value="mpg1_a\nmpg1_b\ntakeyama_a\noperator_a\noperator_b\noperator_c",
        help="1行に1件ずつ入力します。mpg1 を含むものは AI、takeyama を含むものは Form、それ以外を入電として集計します。",
        height=180,
    )
    submit = st.form_submit_button("集計する", type="primary")

if submit:
    creators = [line.strip() for line in creators_text.splitlines() if line.strip()]
    with service_scope() as container:
        result = container.leoc_service.create_snapshot(
            actor_id=user["user_id"],
            snapshot_time=snapshot_time,
            lost_count=int(lost_count),
            creators=creators,
        )
    result["project_name"] = project["label"]
    st.session_state["latest_response_result"] = result

result = st.session_state.get("latest_response_result")
if result:
    st.subheader(f'最新結果: {result["project_name"]}')
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("入電", result["inbound_count"])
    c2.metric("呼損", result["lost_count"])
    c3.metric("応答率", f'{result["answer_rate"]:.1f}%')
    c4.metric("AI", result["ai_count"])
    c5.metric("Form", result["form_count"])

    st.subheader("投稿文")
    st.code(result["post_text"], language="text")
    st.text_area("コピー用テキスト", value=result["post_text"], height=120)
    st.caption("将来は project_name / source_name / queue_name を拡張し、案件別・窓口別の履歴管理へ寄せやすい構造にします。")

st.subheader("履歴")
st.dataframe(history, use_container_width=True, hide_index=True)
