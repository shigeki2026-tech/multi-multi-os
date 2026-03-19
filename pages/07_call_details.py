import streamlit as st

from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in


st.set_page_config(page_title="Call Details", layout="wide")
ensure_app_ready()
ensure_logged_in()

st.title("通話呼詳細データ作成")
st.warning("未実装")
st.selectbox("元データ選択", ["dummy_source.csv"])
st.text_area("条件指定", height=140)
st.text_area("プレビュー", height=200)
st.button("出力（ダミー）", use_container_width=True)
st.info("TODO: 呼詳細加工ジョブと出力機能を実装する。")
