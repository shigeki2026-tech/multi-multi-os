import streamlit as st

st.set_page_config(page_title="応答率速報", layout="wide")

from src.services import answer_rate_service as ar
from src.services.cdr_import_service import CdrImportError
from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar

ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

st.title("応答率速報")

tab_manual, tab_cdr = st.tabs(["手入力", "CDR取込"])

# ===========================================================================
# 手入力タブ（既存 leoc_service。機能は変更しない）
# ===========================================================================
with tab_manual:
    with service_scope() as container:
        project_options = container.master_service.project_options()
        history = container.leoc_service.list_history_for_display()

    st.caption("案件ごとの応答率速報を手入力で集計します。CDRからの自動集計は隣の『CDR取込』タブを使います。")

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

    st.subheader("履歴")
    st.dataframe(history, use_container_width=True, hide_index=True)

# ===========================================================================
# CDR取込タブ（新規）
# 流れ: アップロード → エンコード判定 → 列マッピング確認 → 閾値ルール確認
#       → 集計プレビュー → 保存 → 結果表示 → 報告文生成
# ===========================================================================
with tab_cdr:
    st.caption(
        "通話呼詳細CSV（cp932想定・約22MB/10万行）を取り込み、応答率を自動集計します。"
        "生CSVは編集しません。保存前に必ずプレビューを確認してください。"
    )

    # 現在の閾値ルール（abandon_rules）を確認用に表示
    with service_scope() as container:
        abandon_rows = container.answer_rate_master_service.list_abandon_rules()
    with st.expander("閾値ルール確認（放棄呼の秒数閾値）", expanded=False):
        if abandon_rows:
            st.dataframe(abandon_rows, use_container_width=True, hide_index=True)
        else:
            st.info("abandon_rules は未登録です。全体既定 0 秒として扱います（管理画面で登録できます）。")
        st.caption(ar.ELAPSED_APPROX_NOTE)

    uploaded = st.file_uploader("通話呼詳細CSV", type=["csv"], key="cdr_uploader")

    # 列マッピング（固定マッピングを初期値にし、UIで上書き可能）
    st.markdown("**列マッピング**（CSVの実列名に合わせて調整できます）")
    mapping = {}
    map_cols = st.columns(2)
    for i, (logical, default_col) in enumerate(ar.DEFAULT_COLUMN_MAPPING.items()):
        mapping[logical] = map_cols[i % 2].text_input(logical, value=default_col, key=f"map_{logical}")

    preview_clicked = st.button("集計プレビュー", type="primary", disabled=uploaded is None)

    if preview_clicked and uploaded is not None:
        raw = uploaded.getvalue()  # 生バイト。DataFrameは session_state に保存しない
        try:
            with st.spinner("CSVを読み込み・集計しています..."):
                with service_scope() as container:
                    prepared = container.cdr_import_service.prepare(raw, uploaded.name, mapping)
        except CdrImportError as exc:
            st.error(str(exc))
            st.session_state.pop("cdr_prepared", None)
        else:
            # 集計済みの軽量結果のみ保持（生CSV/DataFrameは保持しない）
            st.session_state["cdr_prepared"] = prepared
            st.session_state["cdr_saved"] = None

    prepared = st.session_state.get("cdr_prepared")
    if prepared:
        st.success(f"エンコード判定: {prepared['encoding']} / 読込行数: {prepared['row_count']:,}")
        s = prepared["summary"]
        # st.metric を狭い4列に詰めると集計グループ数（5桁）が「22,82」のように見切れるため、
        # 主要3指標のみ metric にし、集計グループ数は3桁カンマ付きの通常テキストで全桁表示する。
        m1, m2, m3 = st.columns(3)
        m1.metric("完了呼", f"{s['completed_total']:,}")
        m2.metric("有効放棄呼", f"{s['valid_abandon_total']:,}")
        m3.metric("全体応答率", f"{s['overall_answer_rate']:.1f}%")
        st.markdown(f"**集計グループ数:** {s['stat_group_count']:,} グループ")
        with st.expander("前処理サマリ（検証件数）", expanded=False):
            st.json(s)

        # 放棄呼の秒数閾値（abandon_rules）未登録時の強い警告。
        # 全体既定0秒で集計できてしまうが、正式報告値に影響するため明示する（0秒保存自体は許可）。
        if not abandon_rows:
            st.warning(
                "現在、放棄呼の秒数閾値が未登録のため、全体既定0秒で集計しています。"
                "正式報告に使う場合は、管理画面で閾値ルールを登録してから再集計してください。"
            )

        if prepared["collisions"]:
            st.warning(
                f"既に取込済みのキーが {len(prepared['collisions'])} 件あります。"
                "二重取込になるため、このまま保存はできません（DBのユニーク制約で拒否されます）。"
            )

        stats = prepared["stats"]
        with service_scope() as container:
            merges = container.answer_rate_master_service.list_skill_group_merge()
        active_merges = [m for m in merges if m["is_active"]]

        st.subheader("集計プレビュー")
        v1, v2 = st.columns(2)
        with v1:
            st.markdown("**日別**")
            st.dataframe(ar.by_date(stats), use_container_width=True, hide_index=True)
            st.markdown("**時間帯別**")
            st.dataframe(ar.by_time_slot(stats), use_container_width=True, hide_index=True)
        with v2:
            st.markdown("**スキルグループ別**")
            st.dataframe(ar.by_skill_group(stats), use_container_width=True, hide_index=True)
            st.markdown("**合算ラベル別**（保存せず都度計算）")
            if active_merges:
                st.dataframe(ar.by_merge_label(stats, active_merges), use_container_width=True, hide_index=True)
            else:
                st.caption("skill_group_merge が未登録です（管理画面で登録できます）。")

        st.subheader("保存")
        st.caption("保存すると raw skill_group の集計値のみ call_stats に保存します（合算値は保存しません）。")

        # 二重取込は保存前に検出し、保存操作自体を無効化する。
        # （ボタンを disabled にするため、import_log に failed を残す必要はない。）
        if prepared["collisions"]:
            with service_scope() as container:
                existing_rows = container.call_stats_repository.count_stats()
                last_logs = container.call_stats_repository.list_import_logs(limit=1)
            log_label = f" / import_log #{last_logs[0].id}" if last_logs else ""
            st.warning(
                "このCSVの集計結果は既に保存済みです。"
                "同一期間・同一スキルグループの重複取込を防ぐため、保存できません。\n\n"
                f"既存 call_stats: {existing_rows:,}行{log_label}"
            )

        # 閾値未登録（0秒既定）の場合は保存ボタン直前にも注意を出す（0秒保存自体は許可）。
        if not abandon_rows:
            st.caption(
                "⚠ 放棄呼の秒数閾値が未登録のため、全体既定0秒で集計した値を保存します。"
                "正式報告に使う場合は、管理画面で閾値ルールを登録してから再集計してください。"
            )

        if st.button("この内容で保存する", type="primary", disabled=bool(prepared["collisions"])):
            if uploaded is None:
                st.error("ファイルが見つかりません。再度アップロードしてください。")
            else:
                try:
                    with service_scope() as container:
                        res = container.cdr_import_service.commit(
                            prepared, actor_id=user["user_id"], raw=uploaded.getvalue()
                        )
                except CdrImportError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["cdr_saved"] = res
                    st.success(f"保存しました。call_stats {res['inserted_stat_rows']:,} 行 / import_log #{res['import_log_id']}")

        st.subheader("報告文生成")
        # スキルグループ別が大量に展開されると実務報告文として使いにくいため表示を切替える。
        # 既定は「全体サマリのみ」。集計値そのものは変えず、並べ替え・件数制限のみ。
        report_mode = st.radio(
            "報告文の表示範囲",
            options=list(ar.REPORT_MODES.keys()),
            format_func=lambda k: ar.REPORT_MODES[k],
            index=list(ar.REPORT_MODES.keys()).index(ar.DEFAULT_REPORT_MODE),
            horizontal=True,
            key="cdr_report_mode",
        )
        report_text = ar.build_report_text(stats, merges=active_merges, overall=s, mode=report_mode)
        st.code(report_text, language="text")
        # mode を key に含め、表示範囲を切替えたときにコピー用テキストも追従させる。
        st.text_area("コピー用（報告文）", value=report_text, height=240, key=f"cdr_report_area_{report_mode}")
        st.caption("報告文は決定論テンプレートで生成しています（外部AI未設定でも完結します）。")

    # 取込履歴（import_log）
    with service_scope() as container:
        logs = container.call_stats_repository.list_import_logs(limit=30)
    st.subheader("取込履歴（import_log）")
    st.dataframe(
        [
            {
                "id": lg.id,
                "filename": lg.filename,
                "encoding": lg.encoding,
                "row_count": lg.row_count,
                "status": lg.status,
                "engine_version": lg.engine_version,
                "imported_at": lg.imported_at,
                "error": lg.error_message or "",
            }
            for lg in logs
        ],
        use_container_width=True,
        hide_index=True,
    )
