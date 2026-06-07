import pandas as pd
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

tab_manual, tab_cdr, tab_view = st.tabs(["手入力", "CDR取込", "応答率閲覧"])

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

        # 閾値比較プレビュー（参考値・DB非保存・全体のみ）
        # 正式な秒数閾値を決める前に、同じCSVで 0/3/10/20/30秒の応答率を見比べる。
        comparison = prepared.get("threshold_comparison")
        if comparison:
            st.subheader("閾値比較プレビュー（参考値・保存されません）")
            st.caption(
                "この比較は保存されません。正式値にする場合は、管理画面で abandon_rules を登録し、"
                "既存集計を削除してから再取込してください。"
            )
            comp_view = [
                {
                    "閾値(秒)": r["threshold_seconds"],
                    "完了呼": r["completed_count"],
                    "有効放棄呼": r["valid_abandon_count"],
                    "分母(完了+有効放棄)": r["denominator"],
                    "応答率(%)": r["answer_rate"],
                    "応答率差分(0秒比)": r["answer_rate_diff_from_0"],
                    "有効放棄差分(0秒比)": r["valid_abandon_diff_from_0"],
                }
                for r in comparison
            ]
            st.dataframe(comp_view, use_container_width=True, hide_index=True)
            # 比較表のCSVダウンロード（生の英語キーで出力。集計値そのものは変えない）。
            comp_csv = pd.DataFrame(comparison).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "閾値比較表をCSVダウンロード",
                data=comp_csv,
                file_name="threshold_comparison.csv",
                mime="text/csv",
                key="cdr_threshold_compare_dl",
            )

        # ===================================================================
        # 選択式集計パネル（業務別・参考値・DB非保存）
        # CSV内の skill_group を複数選び、秒数閾値を選ぶと、その回線群の応答率を大きく表示する。
        # 計算は prepare で1度だけ作った中間集計（skill_group×threshold）を合算するだけで、
        # 生CSVは再走査しない（大容量CSV対策）。UI層へORMは渡さない（list[dict]/数値のみ）。
        # ===================================================================
        sg_summary = prepared.get("skill_group_threshold_summary") or []
        skill_groups_all = prepared.get("skill_groups") or sorted({r["skill_group"] for r in sg_summary})
        if sg_summary:
            st.subheader("選択式集計（業務別・参考値・保存されません）")
            st.caption(
                "回線（skill_group）を複数選び、秒数閾値を選ぶと、その回線群の応答率を集計します。"
                "結果は保存されません。正式値にする場合は、管理画面で skill_group_merge（業務名→回線）と "
                "abandon_rules（秒数閾値）を登録し、既存集計を削除してから同じCSVを再取込してください。"
            )

            with service_scope() as container:
                merges_all = container.answer_rate_master_service.list_skill_group_merge()
            existing_labels = sorted({m["merge_label"] for m in merges_all})

            bc1, bc2 = st.columns(2)
            label_choice = bc1.selectbox(
                "業務名（既存の合算ラベルから選択）",
                options=["（新規入力）"] + existing_labels,
                key="sel_label_choice",
            )
            new_label = bc2.text_input("新規業務名（任意）", key="sel_new_label")
            if label_choice != "（新規入力）":
                business_name = label_choice
            else:
                business_name = new_label.strip()

            # 既存ラベルを選んだ場合、その子回線をmultiselectの初期選択にする
            default_children = [
                m["child_skill_group"]
                for m in merges_all
                if m["merge_label"] == label_choice and m["child_skill_group"] in skill_groups_all
            ]

            selected_lines = st.multiselect(
                f"回線（skill_group）を選択　全 {len(skill_groups_all)} 件（入力して検索できます）",
                options=skill_groups_all,
                default=default_children,
                key="sel_lines",
            )
            sc1, sc2 = st.columns(2)
            sc1.caption(f"選択回線数: {len(selected_lines)} 件")
            threshold_sel = sc2.selectbox(
                "秒数閾値",
                options=list(ar.COMPARE_THRESHOLDS),
                index=0,
                format_func=lambda t: f"{t}秒",
                key="sel_threshold",
            )

            if selected_lines:
                sel = ar.summarize_selected_lines(sg_summary, selected_lines, threshold_sel)
                title_suffix = f"（業務名: {business_name}）" if business_name else ""
                st.markdown(f"#### 選択結果：{threshold_sel}秒 / 選択回線 {sel['selected_line_count']} 件{title_suffix}")
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("応答率", f"{sel['answer_rate']:.1f}%")
                b2.metric("完了呼", f"{sel['completed_count']:,}")
                b3.metric("有効放棄呼", f"{sel['valid_abandon_count']:,}")
                b4.metric("分母(完了+有効放棄)", f"{sel['denominator']:,}")

                # 補助: 同じ選択回線群の 0/3/10/20/30秒比較
                st.markdown("**選択回線群の閾値比較（0/3/10/20/30秒）**")
                sel_cmp = ar.compare_selected_lines(sg_summary, selected_lines)
                sel_cmp_view = [
                    {
                        "閾値(秒)": r["threshold_seconds"],
                        "完了呼": r["completed_count"],
                        "有効放棄呼": r["valid_abandon_count"],
                        "分母(完了+有効放棄)": r["denominator"],
                        "応答率(%)": r["answer_rate"],
                        "応答率差分(0秒比)": r["answer_rate_diff_from_0"],
                        "有効放棄差分(0秒比)": r["valid_abandon_diff_from_0"],
                    }
                    for r in sel_cmp
                ]
                st.dataframe(sel_cmp_view, use_container_width=True, hide_index=True)
                sel_csv = pd.DataFrame(sel_cmp).to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "選択回線群の比較表をCSVダウンロード",
                    data=sel_csv,
                    file_name="selected_lines_threshold_comparison.csv",
                    mime="text/csv",
                    key="sel_compare_dl",
                )

                # グループ化導線: 選択回線群を skill_group_merge に登録（任意・既存テーブル利用）
                st.markdown("**この回線群を合算ラベルとして登録（任意）**")
                st.caption(
                    "業務名＝merge_label、選択回線＝child_skill_group として skill_group_merge に登録します"
                    "（既存と重複する組み合わせはスキップ）。応答率の正式値は、abandon_rules 登録後に再取込して算出してください。"
                )
                if not business_name:
                    st.caption("登録するには業務名を入力／選択してください。")
                if st.button(
                    "この回線群を合算ラベルに登録する",
                    disabled=not business_name,
                    key="sel_save_merge",
                ):
                    existing_pairs = {(m["merge_label"], m["child_skill_group"]) for m in merges_all}
                    try:
                        added, skipped = 0, 0
                        with service_scope() as container:
                            for sg in selected_lines:
                                if (business_name, sg) in existing_pairs:
                                    skipped += 1
                                    continue
                                container.answer_rate_master_service.create_skill_group_merge(
                                    user["user_id"], business_name, sg
                                )
                                added += 1
                    except Exception as exc:  # 例外は握りつぶさず表示
                        st.error(f"合算ラベルの登録に失敗しました: {exc}")
                    else:
                        st.success(
                            f"合算ラベル『{business_name}』に {added} 件登録しました"
                            f"（重複スキップ {skipped} 件）。集計の正式値は再取込で算出されます。"
                        )
            else:
                st.info("回線（skill_group）を1件以上選択してください。")

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
            # UI層へSQLAlchemy ORMオブジェクトを渡さない。ImportLogはrepository層でdict化する。
            with service_scope() as container:
                existing_rows = container.call_stats_repository.count_stats()
                last_logs = container.call_stats_repository.latest_import_logs(limit=1)
            log_label = f" / import_log #{last_logs[0]['id']}" if last_logs else ""
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
                    st.success(
                        f"保存しました。call_stats {res['inserted_stat_rows']:,} 行 / "
                        f"閲覧用集計(answer_rate_threshold_stats) {res.get('inserted_threshold_rows', 0):,} 行 / "
                        f"import_log #{res['import_log_id']}"
                    )

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
    # UI層へSQLAlchemy ORMオブジェクトを渡さない。ImportLogはrepository層でdict化する。
    with service_scope() as container:
        logs = container.call_stats_repository.latest_import_logs(limit=30)
    st.subheader("取込履歴（import_log）")
    st.dataframe(logs, use_container_width=True, hide_index=True)

    # -----------------------------------------------------------------------
    # 取込済み集計の削除（再取込用）
    # abandon_rules の秒数閾値を変更した後、既存の0秒集計を削除して同じCSVを再取込する。
    # call_stats と import_log を結ぶFK列は無い（DBスキーマ変更しない方針）ため、
    # 削除は import_log 単位ではなく stat_date 範囲で行う。1CSV=1期間のため実用上これで足りる。
    # 削除対象は raw skill_group の call_stats のみ（合算値は元々非保存）。
    # -----------------------------------------------------------------------
    st.subheader("取込済み集計の削除（再取込用）")
    st.caption(
        "abandon_rules の秒数閾値を変更した後、既存の集計（0秒既定など）を削除して同じCSVを再取込するための機能です。"
        "削除対象は call_stats（正式閾値用）と answer_rate_threshold_stats（閲覧用の0/3/10/20/30秒中間集計）の両方です。"
        "合算値は保存していないため対象外です。削除は取り消せません。"
    )
    with service_scope() as container:
        del_min, del_max = container.call_stats_repository.stat_date_range()
        # call_stats が空でも閲覧用集計だけ残るケースに備え、両方の範囲を考慮する。
        th_min, th_max = container.answer_rate_threshold_repository.stat_date_range()
    _mins = [d for d in (del_min, th_min) if d is not None]
    _maxs = [d for d in (del_max, th_max) if d is not None]
    del_min = min(_mins) if _mins else None
    del_max = max(_maxs) if _maxs else None

    if del_min is None:
        st.info("削除できる集計がありません（まだ取込がありません）。")
    else:
        with st.expander("取込履歴を参照（削除する期間の特定用）", expanded=False):
            st.dataframe(logs, use_container_width=True, hide_index=True)
        dc1, dc2 = st.columns(2)
        del_start = dc1.date_input(
            "削除開始日（stat_date）", value=del_min, min_value=del_min, max_value=del_max, key="cdr_del_start"
        )
        del_end = dc2.date_input(
            "削除終了日（stat_date）", value=del_max, min_value=del_min, max_value=del_max, key="cdr_del_end"
        )
        if del_start > del_end:
            st.warning("削除開始日は終了日以前にしてください。")
        else:
            with service_scope() as container:
                del_count = container.call_stats_repository.count_stats_in_range(del_start, del_end)
                del_th_count = container.answer_rate_threshold_repository.count_in_range(del_start, del_end)
            dm1, dm2 = st.columns(2)
            dm1.markdown(f"**削除対象 call_stats: {del_count:,} 行**")
            dm2.markdown(f"**削除対象 閲覧用集計: {del_th_count:,} 行**")
            st.caption(f"対象期間（stat_date）: {del_start} 〜 {del_end}")
            # 削除前の確認チェックを必須にする（チェックが無いと削除ボタンを押せない）。
            del_confirm = st.checkbox(
                "上記の集計（call_stats と閲覧用集計）を削除することを確認しました（取り消せません）",
                key="cdr_del_confirm",
            )
            if st.button(
                "集計を削除する",
                type="secondary",
                disabled=((del_count == 0 and del_th_count == 0) or not del_confirm),
            ):
                try:
                    with service_scope() as container:
                        del_res = container.cdr_import_service.delete_call_stats_range(
                            del_start, del_end, actor_id=user["user_id"]
                        )
                except Exception as exc:  # 例外は握りつぶさず理由を表示する
                    st.error(f"削除に失敗しました: {exc}")
                else:
                    # 古いプレビュー結果（衝突情報）は無効化し、再プレビューから取込し直させる。
                    st.session_state.pop("cdr_prepared", None)
                    st.session_state["cdr_saved"] = None
                    st.success(
                        f"call_stats {del_res['deleted_rows']:,} 行 / "
                        f"閲覧用集計 {del_res.get('deleted_threshold_rows', 0):,} 行を削除しました"
                        f"（import_log #{del_res['import_log_id']} に記録）。"
                        "同じCSVを『集計プレビュー』からやり直して再取込できます。"
                    )
                    st.rerun()

# ===========================================================================
# 応答率閲覧タブ（新規）
# 取込時に保存した中間集計 answer_rate_threshold_stats から、CSVを再アップロードせずに
# 期間・業務名(合算ラベル)・回線(skill_group)・秒数閾値を選んで応答率を表示する。
# 合算値は保存しない。選択回線の completed/valid_abandon を都度合算し応答率を再計算する。
# UI層へSQLAlchemy ORMは渡さない（repositoryがdict/数値で返す）。
# ===========================================================================
with tab_view:
    st.caption(
        "取込済みの集計データから応答率を閲覧します（CSVの再アップロードは不要）。"
        "期間・業務名・回線（skill_group）・秒数閾値を選ぶと、保存済みの中間集計を合算して計算します。"
    )

    with service_scope() as container:
        v_has_data = container.answer_rate_threshold_repository.has_data()
        v_min, v_max = container.answer_rate_threshold_repository.stat_date_range()

    if not v_has_data or v_min is None:
        st.info(
            "閲覧できる集計データがありません。『CDR取込』タブでCSVを取り込むと、"
            "0/3/10/20/30秒の中間集計（answer_rate_threshold_stats）が保存され、ここで閲覧できるようになります。"
        )
    else:
        # 1. 対象期間
        pc1, pc2 = st.columns(2)
        view_start = pc1.date_input(
            "対象期間 開始（stat_date）", value=v_min, min_value=v_min, max_value=v_max, key="view_start"
        )
        view_end = pc2.date_input(
            "対象期間 終了（stat_date）", value=v_max, min_value=v_min, max_value=v_max, key="view_end"
        )
        if view_start > view_end:
            st.warning("対象期間の開始日は終了日以前にしてください。")
        else:
            # 期間内に存在する回線と、業務名（合算ラベル）を取得
            with service_scope() as container:
                available_lines = container.answer_rate_threshold_repository.list_skill_groups(
                    view_start, view_end
                )
                merges_all = container.answer_rate_master_service.list_skill_group_merge()
            active_merges = [m for m in merges_all if m["is_active"]]
            merge_labels = sorted({m["merge_label"] for m in active_merges})

            # 2. 業務名（合算ラベル）。選ぶと配下の skill_group を回線選択の初期値にする。
            label_choice = st.selectbox(
                "業務名（合算ラベル skill_group_merge から選択。配下の回線が下の選択に入ります）",
                options=["（指定なし）"] + merge_labels,
                key="view_label_choice",
            )
            default_lines = [
                m["child_skill_group"]
                for m in active_merges
                if m["merge_label"] == label_choice and m["child_skill_group"] in available_lines
            ]
            if label_choice != "（指定なし）" and not default_lines:
                st.caption(
                    f"※ 業務名『{label_choice}』配下の回線は、対象期間の集計データに含まれていません。"
                )

            # 3/4. 回線（skill_group）の複数選択（業務名の配下を初期値、直接選択も可）
            selected_lines = st.multiselect(
                f"回線（skill_group）を選択　全 {len(available_lines)} 件（入力して検索できます）",
                options=available_lines,
                default=default_lines,
                key="view_lines",
            )

            # 5. 秒数閾値
            threshold_sel = st.selectbox(
                "秒数閾値",
                options=list(ar.COMPARE_THRESHOLDS),
                index=0,
                format_func=lambda t: f"{t}秒",
                key="view_threshold",
            )

            if not selected_lines:
                st.info("回線（skill_group）を1件以上選択してください（業務名を選ぶと自動で入ります）。")
            else:
                with service_scope() as container:
                    agg = container.answer_rate_threshold_repository.aggregate_selected(
                        view_start, view_end, selected_lines, threshold_sel
                    )
                    cmp_rows = container.answer_rate_threshold_repository.compare_selected(
                        view_start, view_end, selected_lines
                    )
                completed = agg["completed_count"]
                valid_abandon = agg["valid_abandon_count"]
                denom = completed + valid_abandon
                rate = ar.answer_rate(completed, valid_abandon)

                # 6. 選択結果を大きく表示
                st.markdown(
                    f"#### 選択結果：{threshold_sel}秒 / 対象期間 {view_start} 〜 {view_end} / "
                    f"選択回線 {len(selected_lines)} 件"
                )
                b1, b2, b3, b4, b5 = st.columns(5)
                b1.metric("応答率", f"{rate:.1f}%")
                b2.metric("完了呼", f"{completed:,}")
                b3.metric("有効放棄呼", f"{valid_abandon:,}")
                b4.metric("分母(完了+有効放棄)", f"{denom:,}")
                b5.metric("選択回線数", f"{len(selected_lines):,}")

                if denom == 0:
                    st.warning("選択回線・期間・閾値に該当する集計がありません（完了呼・有効放棄呼が0）。")

                # 7. 0/3/10/20/30秒の比較表（同じ回線群・同じ期間。0秒基準の差分付き）
                st.markdown("**選択回線群の閾値比較（0/3/10/20/30秒）**")
                by_threshold = {r["threshold_seconds"]: r for r in cmp_rows}
                cmp_view = []
                baseline_rate = None
                baseline_abandon = None
                for t in ar.COMPARE_THRESHOLDS:
                    r = by_threshold.get(t, {"completed_count": 0, "valid_abandon_count": 0})
                    c = r["completed_count"]
                    va = r["valid_abandon_count"]
                    d = c + va
                    rt = ar.answer_rate(c, va)
                    if t == 0:
                        baseline_rate = rt
                        baseline_abandon = va
                    cmp_view.append(
                        {
                            "閾値(秒)": t,
                            "完了呼": c,
                            "有効放棄呼": va,
                            "分母(完了+有効放棄)": d,
                            "応答率(%)": rt,
                            "応答率差分(0秒比)": (
                                round(rt - baseline_rate, 1) if baseline_rate is not None else 0.0
                            ),
                            "有効放棄差分(0秒比)": (
                                va - baseline_abandon if baseline_abandon is not None else 0
                            ),
                        }
                    )
                st.dataframe(cmp_view, use_container_width=True, hide_index=True)
                cmp_csv = pd.DataFrame(cmp_view).to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "閾値比較表をCSVダウンロード",
                    data=cmp_csv,
                    file_name="view_threshold_comparison.csv",
                    mime="text/csv",
                    key="view_compare_dl",
                )
                st.caption(
                    "比較表は同じ回線群・同じ対象期間の0/3/10/20/30秒応答率です。"
                    "合算値は保存しておらず、選択回線の集計値を都度合算して計算しています。"
                )
