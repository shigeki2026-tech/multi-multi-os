import streamlit as st

from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar


st.set_page_config(
    page_title="ホーム",
    page_icon="MM",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("ホーム")
st.caption("マルチ業務OSの利用案内です。")

st.success("左のメニューから画面を選択してください。")

col1, col2 = st.columns([1.3, 1])
with col1:
    st.subheader("このアプリで扱うもの")
    st.markdown(
        """
        - ダッシュボードで今日やることを確認
        - タスクの追加、編集、状態更新
        - SV依頼の作成と進捗確認
        - カレンダーの予定表示
        - 応答率速報の集計と履歴確認
        - 日報送信の作成、プレビュー、送信履歴確認
        """
    )

with col2:
    st.subheader("運用メモ")
    st.info("予定はカレンダー、日次でやることはタスクと依頼から確認します。")
    st.info("ユーザー、チーム、プロジェクトはアプリDBで管理し、権限と所属もDBを正本として扱います。")
