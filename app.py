import streamlit as st

from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, logout


st.set_page_config(
    page_title="MultiMulti OS",
    page_icon="MM",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_app_ready()

st.title("MultiMulti OS")
st.caption("マルチ業務部向け業務ハブ MVP")

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
- タスクの登録、編集、担当変更、進捗更新
- SV依頼の作成と対応状況の管理
- Google Calendar の予定参照
- LEOC速報の作成
- 日報の作成、プレビュー、Gmail送信、履歴確認
"""
)
