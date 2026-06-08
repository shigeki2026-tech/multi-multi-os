"""CT-e1自動化（Phase 0確認 / CSV呼損チェック / 設定 / 実行ログ）。

今回の範囲は確認画面とCSV呼損チェックまで。CT-e1 Suiteへの自動操作・API連携・
Teams本送信は実装しない（通知文プレビューのみ）。集計は src.services.ct_e1_service の
純粋関数に委譲する（このページは入出力のみ）。
"""
import streamlit as st

st.set_page_config(page_title="CT-e1自動化", layout="wide")

from src.services import ct_e1_service as cte
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar

ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

store = cte.CtE1Store()

st.title("CT-e1自動化")
st.caption(
    "CT-e1業務の「定時拘束ゼロ」に向けた土台です。今回は Phase 0確認 と CSV呼損チェック までを提供します"
    "（自動ログイン・GUI自動化・Teams本送信は未実装）。"
)

tab_phase0, tab_csv, tab_settings, tab_log = st.tabs(
    ["1. Phase 0確認", "2. CSV呼損チェック", "3. 設定", "4. 実行ログ"]
)


# ---------------------------------------------------------------------------
# 1. Phase 0確認
# ---------------------------------------------------------------------------
with tab_phase0:
    st.subheader("Phase 0確認")
    st.caption("自動化の前提条件を確認します。入力内容は保存できます（DBではなくJSONファイル保存）。")

    saved = store.load_phase0()
    with st.form("ct_e1_phase0_form"):
        values: dict = {}
        cols = st.columns(2)
        for i, item in enumerate(cte.PHASE0_ITEMS):
            with cols[i % 2]:
                values[item] = st.text_input(item, value=str(saved.get(item, "")))
        submitted = st.form_submit_button("Phase 0確認を保存", type="primary")
    if submitted:
        store.save_phase0(values)
        st.success("Phase 0確認を保存しました。")
    if saved.get("_updated_at"):
        st.caption(f"最終更新: {saved['_updated_at']}")


# ---------------------------------------------------------------------------
# 2. CSV呼損チェック
# ---------------------------------------------------------------------------
with tab_csv:
    st.subheader("CSV呼損チェック")
    st.caption(
        "呼損量＝放棄呼のみ。『放棄呼』列が 1 の行だけを集計します。"
        "『発信呼』列があれば 発信呼=1 は除外します。必須列: "
        f"{', '.join(cte.REQUIRED_COLUMNS)}。"
    )

    settings = store.load_settings()
    default_threshold = int(settings.get("threshold", 0) or 0)
    target_groups_raw = settings.get("target_skill_groups") or ""

    threshold = st.number_input(
        "しきい値（スキルグループ別の放棄呼数がこの値以上でアラート）",
        min_value=0,
        value=default_threshold,
        step=1,
    )
    use_target = st.checkbox(
        "対象スキルグループのみに絞る（設定タブの『対象スキルグループ』を使用）",
        value=bool(target_groups_raw.strip()),
    )
    target_skill_groups = None
    if use_target and target_groups_raw.strip():
        target_skill_groups = [s.strip() for s in target_groups_raw.splitlines() if s.strip()]
        st.caption(f"対象: {len(target_skill_groups)}グループ")

    uploaded = st.file_uploader("呼損確認用CSVをアップロード", type=["csv"])

    if uploaded is not None:
        raw = uploaded.getvalue()
        try:
            encoding, df = cte.detect_and_read(raw)
        except cte.CtE1Error as exc:
            st.error(str(exc))
        else:
            missing = cte.validate_columns(df.columns)
            if missing:
                st.error(f"必須列が見つかりません: {', '.join(missing)}")
            else:
                result = cte.aggregate_call_loss(
                    df, threshold=int(threshold), target_skill_groups=target_skill_groups
                )

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("読込文字コード", encoding)
                m2.metric("総行数", f"{result['total_rows']:,}")
                m3.metric(
                    "発信呼除外数",
                    f"{result['outbound_excluded']:,}" if result["has_outbound_column"] else "—",
                )
                m4.metric("放棄呼数（呼損量）", f"{result['abandon_count']:,}")
                if not result["has_outbound_column"]:
                    st.caption("『発信呼』列が無いため発信呼の除外は行っていません。")

                st.markdown("##### スキルグループ別 放棄呼数")
                if result["by_skill_group"]:
                    st.dataframe(result["by_skill_group"], use_container_width=True, hide_index=True)
                else:
                    st.info("放棄呼はありませんでした。")

                st.markdown(f"##### しきい値（{int(threshold)}）以上のアラート対象")
                if result["alerts"]:
                    st.dataframe(result["alerts"], use_container_width=True, hide_index=True)
                else:
                    st.success("しきい値超過なし")

                st.markdown("##### 通知文プレビュー（Teamsへの送信は行いません）")
                preview = cte.build_notification_text(result)
                st.code(preview, language="text")

                if st.button("この結果を実行ログに保存", type="primary"):
                    store.append_log(
                        {
                            "filename": uploaded.name,
                            "encoding": encoding,
                            "total_rows": result["total_rows"],
                            "outbound_excluded": result["outbound_excluded"],
                            "abandon_count": result["abandon_count"],
                            "threshold": int(threshold),
                            "alert_count": len(result["alerts"]),
                            "actor": user.get("display_name"),
                        }
                    )
                    st.success("実行ログに保存しました。")


# ---------------------------------------------------------------------------
# 3. 設定
# ---------------------------------------------------------------------------
with tab_settings:
    st.subheader("設定")
    st.caption("CSV呼損チェックの既定しきい値・対象スキルグループ・Teams通知先を保存します（JSONファイル保存）。")

    settings = store.load_settings()
    with st.form("ct_e1_settings_form"):
        threshold_setting = st.number_input(
            "既定しきい値",
            min_value=0,
            value=int(settings.get("threshold", 0) or 0),
            step=1,
        )
        target_setting = st.text_area(
            "対象スキルグループ（1行に1つ。空なら全グループ対象）",
            value=str(settings.get("target_skill_groups", "")),
            height=160,
        )
        teams_to = st.text_input("Teams通知先（メモ。本送信は未実装）", value=str(settings.get("teams_to", "")))
        saved_settings = st.form_submit_button("設定を保存", type="primary")
    if saved_settings:
        store.save_settings(
            {
                "threshold": int(threshold_setting),
                "target_skill_groups": target_setting,
                "teams_to": teams_to,
            }
        )
        st.success("設定を保存しました。")
    if settings.get("_updated_at"):
        st.caption(f"最終更新: {settings['_updated_at']}")


# ---------------------------------------------------------------------------
# 4. 実行ログ
# ---------------------------------------------------------------------------
with tab_log:
    st.subheader("実行ログ")
    st.caption("CSV呼損チェックの実行履歴（新しい順）。生CSVは保存せず、集計サマリのみ残します。")
    logs = store.list_logs()
    if logs:
        st.dataframe(logs, use_container_width=True, hide_index=True)
    else:
        st.info("まだ実行ログはありません。")
