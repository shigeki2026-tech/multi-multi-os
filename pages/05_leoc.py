import streamlit as st

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in


st.set_page_config(page_title="LEOC", layout="wide")
ensure_app_ready()
user = ensure_logged_in()

st.title("LEOC応答率把握ツール")

with st.form("leoc_form"):
    c1, c2 = st.columns(2)
    snapshot_time = c1.selectbox("時点", ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"])
    lost_count = c2.number_input("呼損件数", min_value=0, step=1, value=0)
    creators_text = st.text_area(
        "作成者一覧",
        value="mpg1_a\nmpg1_b\ntakeyama_a\noperator_a\noperator_b\noperator_c",
        help="1行1件。mpg1 を含むと AI、takeyama を含むと Form、それ以外は入電として集計します。",
        height=180,
    )
    submit = st.form_submit_button("集計実行", use_container_width=True)

if submit:
    creators = [line.strip() for line in creators_text.splitlines() if line.strip()]
    with service_scope() as container:
        result = container.leoc_service.create_snapshot(
            actor_id=user["user_id"],
            snapshot_time=snapshot_time,
            lost_count=int(lost_count),
            creators=creators,
        )
    st.session_state["latest_leoc_result"] = result

result = st.session_state.get("latest_leoc_result")
if result:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("入電", result["inbound_count"])
    c2.metric("呼損", result["lost_count"])
    c3.metric("応答率", f'{result["answer_rate"]:.1f}%')
    c4.metric("AI", result["ai_count"])
    c5.metric("Form", result["form_count"])

    st.subheader("投稿文")
    st.code(result["post_text"], language="text")
    st.text_area("コピー用テキスト", value=result["post_text"], height=120)
    st.caption("テキストエリアからそのままコピーできます。")

st.subheader("直近履歴")
with service_scope() as container:
    history = container.leoc_service.list_history_for_display()

if history:
    latest_three = history[:3]
    tabs = st.tabs([f'{item["snapshot_time"]} / {item["answer_rate"]:.1f}%' for item in latest_three])
    for tab, item in zip(tabs, latest_three):
        with tab:
            st.code(item["post_text"], language="text")
            st.caption(f'入電 {item["inbound_count"]} / 呼損 {item["lost_count"]} / AI {item["ai_count"]} / Form {item["form_count"]}')

st.dataframe(history, use_container_width=True, hide_index=True)
