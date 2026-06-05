import streamlit as st



st.set_page_config(
    page_title="ホーム",
    page_icon="MM",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.services import answer_rate_service as ar
from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar

ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("ホーム")
st.caption("応答率を中心としたサマリです。今日やること・予定の詳細はダッシュボードを参照してください。")

# --- 応答率サマリ（実データ） ---
with service_scope() as container:
    latest_date = container.call_stats_repository.latest_stat_date()
    cdr_rows = container.call_stats_repository.list_stats(latest_date, latest_date) if latest_date else []
    last_logs = container.call_stats_repository.list_import_logs(limit=1)
    manual_latest = container.leoc_service.latest_for_dashboard()

cdr_completed = sum(r.completed_count for r in cdr_rows)
cdr_valid_abandon = sum(r.valid_abandon_count for r in cdr_rows)
cdr_rate = ar.answer_rate(cdr_completed, cdr_valid_abandon) if cdr_rows else None

st.subheader("応答率（CDR取込・自動集計）")
m1, m2, m3 = st.columns(3)
m1.metric("対象日", str(latest_date) if latest_date else "-")
m2.metric("応答率", f"{cdr_rate:.1f}%" if cdr_rate is not None else "-")
m3.metric("完了 / 有効放棄", f"{cdr_completed:,} / {cdr_valid_abandon:,}" if cdr_rows else "-")
if last_logs:
    lg = last_logs[0]
    st.caption(f"最終取込: {lg.filename}（{lg.status} / {lg.imported_at}）")
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
