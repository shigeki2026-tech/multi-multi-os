import streamlit as st

from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar


st.set_page_config(page_title="呼詳細作成", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("呼詳細作成")
st.warning("未実装")
st.selectbox("元データ選択", ["dummy_source.csv"])
st.text_area("条件指定", height=140)
st.text_area("プレビュー", height=200)
st.button("出力する", use_container_width=True)
st.info("TODO: 呼詳細加工ジョブと出力処理を実装します。")
