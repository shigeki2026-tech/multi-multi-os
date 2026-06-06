import streamlit as st



st.set_page_config(
    page_title="ホーム",
    page_icon="MM",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar

ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("ホーム")
st.caption("応答率を中心としたサマリです。今日やること・予定の詳細はダッシュボードを参照してください。")

# --- 応答率サマリ（実データ） ---
# ORM行はサービス層（DBセッション内）で集計済みdictに変換して受け取る。
# app.py では ORM 属性を一切読まない（DetachedInstanceError 防止）。
with service_scope() as container:
    cdr = container.dashboard_service.get_answer_rate_dashboard_summary()
    manual_latest = container.leoc_service.latest_for_dashboard()

st.subheader("応答率（CDR取込・自動集計）")
m1, m2, m3 = st.columns(3)
m1.metric("対象日", cdr["latest_date"] or "-")
m2.metric("応答率", f"{cdr['answer_rate']:.1f}%" if cdr["answer_rate"] is not None else "-")
m3.metric(
    "完了 / 有効放棄",
    f"{cdr['completed_count']:,} / {cdr['valid_abandon_count']:,}" if cdr["has_data"] else "-",
)
if cdr["latest_import_id"] is not None:
    st.caption(
        f"最終取込: {cdr['latest_import_filename']}"
        f"（{cdr['latest_import_status']} / {cdr['latest_import_at']}）"
    )
else:
    st.caption("まだCDR取込はありません。『応答率速報 → CDR取込』タブから取り込めます。")

col1, col2 = st.columns([1.3, 1])
with col1:
    st.subheader("このアプリで扱うもの")
    st.markdown(
        """
        - ダッシュボードで今日やることを確認
        - タスクの追加、編集、状態更新
        - SV依頼の作成と進捗確認
        - カレンダーの予定表示
        - 応答率速報（手入力／CDR取込）の集計と履歴確認
        - 日報作成（作成・プレビュー・コピー・ファイル出力・履歴保存）
        """
    )

with col2:
    st.subheader("運用メモ")
    st.info("ホームは応答率中心のサマリ、ダッシュボードはタスク・予定中心で役割を分けています。")
    st.info("ユーザー、チーム、プロジェクトはアプリDBで管理し、権限と所属もDBを正本として扱います。")
    if manual_latest:
        st.caption(f"手入力の最新応答率: {manual_latest['answer_rate']}")
