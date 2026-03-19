import streamlit as st

from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, logout


st.set_page_config(
    page_title="ホーム",
    page_icon="MM",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_app_ready()

st.title("ホーム")
st.caption("マルチ業務部の業務ハブ")

user = ensure_logged_in()

with st.sidebar:
    st.subheader("ログイン中")
    st.write(user["display_name"])
    st.write(f'権限: {user["role"]}')
    if st.button("ログアウト", use_container_width=True):
        logout()
        st.rerun()

st.success("左のメニューから画面を選択してください。")
st.markdown(
    """
### 利用できる機能
- ダッシュボードで今日やることを確認
- タスクの追加、編集、状態変更、優先度変更
- SV依頼の作成と対応状況の管理
- カレンダーの予定確認
- 応答率速報の集計
- 日報送信の作成、プレビュー、Gmail送信
- 呼詳細作成の準備画面
"""
)
