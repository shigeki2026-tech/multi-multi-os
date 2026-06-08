import io

import pandas as pd
import streamlit as st



ROLES = ["admin", "sv"]


def badge(label: str, color: str, filled: bool = True) -> str:
    if filled:
        style = f"background:{color};color:#ffffff;border:1px solid {color};"
    else:
        style = f"background:#ffffff;color:{color};border:1px solid {color};"
    return (
        f"<span style='display:inline-block;padding:0.12rem 0.5rem;margin-right:0.2rem;"
        f"border-radius:999px;font-size:0.76rem;font-weight:700;{style}'>{label}</span>"
    )


def color_chip(color: str) -> str:
    return (
        f"<span style='display:inline-block;width:12px;height:12px;border-radius:999px;"
        f"background:{color};border:1px solid rgba(0,0,0,0.15);margin-right:0.35rem;vertical-align:middle;'></span>"
    )


st.set_page_config(page_title="管理", layout="wide")

from src.services.answer_rate_master_service import (
    DEFAULT_GROUP_CANDIDATE_KEYWORDS,
    DEFAULT_REGION_KEYWORDS,
)

# この件数以上の候補は「分割候補を表示」expander を出す（大きすぎる候補の分割登録用）。
SPLIT_SUGGEST_MIN_LINES = 30
from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_admin, ensure_logged_in, render_sidebar
ensure_app_ready()
user = ensure_logged_in()
ensure_admin(user)
render_sidebar(user)

with service_scope() as container:
    apps = container.admin_service.list_apps()
    audit_logs = container.audit_service.list_audit_logs_for_display()
    response_history = container.leoc_service.list_history_for_display()
    team_options = container.master_service.team_options()
    team_rows = container.master_service.list_teams_for_admin()
    project_rows = container.master_service.list_projects_for_admin()
    user_rows = container.master_service.list_users_for_admin()
    exclude_rows = container.answer_rate_master_service.list_exclude_numbers()
    abandon_rows = container.answer_rate_master_service.list_abandon_rules()
    merge_rows = container.answer_rate_master_service.list_skill_group_merge()
    operator_rows = container.answer_rate_master_service.list_operators()
    # 業務グループ登録の子スキルグループ候補（取込済み中間集計に実在する回線）
    skill_group_options = container.answer_rate_threshold_repository.list_skill_groups()

st.title("管理")
st.caption("利用者マスタ、チームマスタ、プロジェクトマスタ、監査ログを確認します。")

project_map = {row["project_id"]: row for row in project_rows}
user_map = {row["user_id"]: row for row in user_rows}
team_map = {row["team_id"]: row for row in team_rows}

st.subheader("ユーザーマスタ")
with st.container(border=True):
    top_cols = st.columns([1.2, 4.8])
    if top_cols[0].button("+ ユーザー追加", type="primary"):
        st.session_state["show_user_create"] = not st.session_state.get("show_user_create", False)
        st.session_state.pop("editing_user_id", None)
        st.rerun()
    top_cols[1].caption("表示名、権限、所属チーム、有効無効を管理します。Googleメールは read-only です。")

    if st.session_state.get("show_user_create", False):
        with st.form("create_user_form", clear_on_submit=True):
            st.markdown("### 新規ユーザー")
            display_name = st.text_input("表示名")
            google_email = st.text_input("Googleメール")
            row1 = st.columns(3)
            role = row1[0].selectbox("権限", ROLES, index=1)
            team = row1[1].selectbox("所属チーム", options=team_options, format_func=lambda item: item["label"])
            is_active = row1[2].checkbox("有効", value=True)
            action = st.columns(2)
            save_user_create = action[0].form_submit_button("追加する", type="primary")
            close_user_create = action[1].form_submit_button("閉じる")
            if close_user_create:
                st.session_state["show_user_create"] = False
                st.rerun()
            if save_user_create:
                if not display_name.strip() or not google_email.strip():
                    st.warning("表示名と Googleメール を入力してください。")
                else:
                    try:
                        with service_scope() as container:
                            container.master_service.create_user(
                                user["user_id"],
                                {
                                    "display_name": display_name.strip(),
                                    "google_email": google_email.strip(),
                                    "role": role,
                                    "team_id": team["value"],
                                    "is_active": is_active,
                                },
                            )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state["show_user_create"] = False
                        st.success("ユーザーを追加しました。")
                        st.rerun()

    header = st.columns([1.4, 1.6, 0.9, 1.3, 0.9, 1.1, 0.8])
    labels = ["表示名", "Googleメール", "権限", "所属チーム", "状態", "最終ログイン", "操作"]
    for col, label in zip(header, labels):
        col.markdown(f"**{label}**")

    for row in user_rows:
        cols = st.columns([1.4, 1.6, 0.9, 1.3, 0.9, 1.1, 0.8])
        cols[0].write(row["display_name"])
        cols[1].caption(row["google_email"])
        cols[2].markdown(
            badge("admin", "#2563EB") if row["role"] == "admin" else badge("sv", "#64748B"),
            unsafe_allow_html=True,
        )
        cols[3].write(row["team_name"])
        cols[4].markdown(
            badge("有効", "#16A34A") if row["is_active"] else badge("無効", "#6B7280"),
            unsafe_allow_html=True,
        )
        cols[5].caption(str(row["last_login_at"] or "-"))
        if cols[6].button("編集", key=f"edit_user_{row['user_id']}"):
            st.session_state["editing_user_id"] = row["user_id"]
            st.session_state["show_user_create"] = False
            st.rerun()

    editing_user_id = st.session_state.get("editing_user_id")
    if editing_user_id and editing_user_id in user_map:
        current = user_map[editing_user_id]
        with st.expander(f"ユーザー編集中: {current['display_name']}", expanded=True):
            with st.form("edit_user_form"):
                display_name = st.text_input("表示名", value=current["display_name"])
                st.text_input("Googleメール", value=current["google_email"], disabled=True)
                row1 = st.columns(3)
                role = row1[0].selectbox("権限", ROLES, index=ROLES.index(current["role"]))
                team = row1[1].selectbox(
                    "所属チーム",
                    options=team_options,
                    index=next((idx for idx, item in enumerate(team_options) if item["value"] == current["team_id"]), 0),
                    format_func=lambda item: item["label"],
                )
                is_active = row1[2].checkbox("有効", value=current["is_active"])
                action = st.columns(2)
                save_user = action[0].form_submit_button("更新する", type="primary")
                close_user = action[1].form_submit_button("閉じる")
                if close_user:
                    st.session_state.pop("editing_user_id", None)
                    st.rerun()
                if save_user:
                    with service_scope() as container:
                        container.master_service.update_user(
                            editing_user_id,
                            user["user_id"],
                            {
                                "display_name": display_name.strip(),
                                "role": role,
                                "team_id": team["value"],
                                "is_active": is_active,
                            },
                        )
                    st.session_state.pop("editing_user_id", None)
                    st.success("ユーザー設定を更新しました。")
                    st.rerun()

st.subheader("チームマスタ")
with st.container(border=True):
    top_cols = st.columns([1.2, 4.8])
    if top_cols[0].button("+ チーム追加", type="primary"):
        st.session_state["show_team_create"] = not st.session_state.get("show_team_create", False)
        st.session_state.pop("editing_team_id", None)
        st.rerun()
    top_cols[1].caption("追加・編集・有効無効変更は監査ログに before / after を保存します。")

    if st.session_state.get("show_team_create", False):
        with st.form("create_team_form", clear_on_submit=True):
            st.markdown("### 新規チーム")
            team_name = st.text_input("チーム名")
            row1 = st.columns(3)
            display_order = row1[0].number_input("表示順", min_value=0, step=10, value=10)
            is_active = row1[1].checkbox("有効", value=True)
            description = row1[2].text_input("説明")
            action = st.columns(2)
            save_team = action[0].form_submit_button("追加する", type="primary")
            close_team = action[1].form_submit_button("閉じる")
            if close_team:
                st.session_state["show_team_create"] = False
                st.rerun()
            if save_team:
                if not team_name.strip():
                    st.warning("チーム名を入力してください。")
                else:
                    with service_scope() as container:
                        container.master_service.create_team(
                            user["user_id"],
                            {
                                "team_name": team_name.strip(),
                                "display_order": int(display_order),
                                "is_active": is_active,
                                "description": description.strip(),
                            },
                        )
                    st.session_state["show_team_create"] = False
                    st.success("チームを追加しました。")
                    st.rerun()

    header = st.columns([1.8, 0.9, 0.9, 1.8, 0.8])
    labels = ["チーム名", "表示順", "状態", "説明", "操作"]
    for col, label in zip(header, labels):
        col.markdown(f"**{label}**")

    for row in team_rows:
        cols = st.columns([1.8, 0.9, 0.9, 1.8, 0.8])
        cols[0].write(row["team_name"])
        cols[1].caption(f"順序 {row['display_order']}")
        cols[2].markdown(
            badge("有効", "#16A34A") if row["is_active"] else badge("無効", "#6B7280"),
            unsafe_allow_html=True,
        )
        cols[3].caption(row["description"] or "-")
        if cols[4].button("編集", key=f"edit_team_{row['team_id']}"):
            st.session_state["editing_team_id"] = row["team_id"]
            st.session_state["show_team_create"] = False
            st.rerun()

    editing_team_id = st.session_state.get("editing_team_id")
    if editing_team_id and editing_team_id in team_map:
        current = team_map[editing_team_id]
        with st.expander(f"チーム編集中: {current['team_name']}", expanded=True):
            with st.form("edit_team_form"):
                team_name = st.text_input("チーム名", value=current["team_name"])
                row1 = st.columns(3)
                display_order = row1[0].number_input("表示順", min_value=0, step=10, value=int(current["display_order"]))
                is_active = row1[1].checkbox("有効", value=current["is_active"])
                description = row1[2].text_input("説明", value=current["description"])
                action = st.columns(2)
                save_edit = action[0].form_submit_button("更新する", type="primary")
                close_edit = action[1].form_submit_button("閉じる")
                if close_edit:
                    st.session_state.pop("editing_team_id", None)
                    st.rerun()
                if save_edit:
                    with service_scope() as container:
                        container.master_service.update_team(
                            editing_team_id,
                            user["user_id"],
                            {
                                "team_name": team_name.strip(),
                                "display_order": int(display_order),
                                "is_active": is_active,
                                "description": description.strip(),
                            },
                        )
                    st.session_state.pop("editing_team_id", None)
                    st.success("チームを更新しました。")
                    st.rerun()

st.subheader("プロジェクトマスタ")
with st.container(border=True):
    top_cols = st.columns([1.2, 4.8])
    if top_cols[0].button("+ プロジェクト追加", type="primary"):
        st.session_state["show_project_create"] = not st.session_state.get("show_project_create", False)
        st.session_state.pop("editing_project_id", None)
        st.rerun()
    top_cols[1].caption("追加・編集・有効無効変更は監査ログに before / after を保存します。")

    if st.session_state.get("show_project_create", False):
        with st.form("create_project_form", clear_on_submit=True):
            st.markdown("### 新規プロジェクト")
            project_name = st.text_input("プロジェクト名")
            row1 = st.columns(3)
            team = row1[0].selectbox("チーム", options=team_options, format_func=lambda x: x["label"])
            color = row1[1].color_picker("色", value="#4F8CFF")
            display_order = row1[2].number_input("表示順", min_value=0, step=10, value=10)
            is_active = st.checkbox("有効", value=True)
            action = st.columns(2)
            save_create = action[0].form_submit_button("追加する", type="primary")
            close_create = action[1].form_submit_button("閉じる")
            if close_create:
                st.session_state["show_project_create"] = False
                st.rerun()
            if save_create:
                if not project_name.strip():
                    st.warning("プロジェクト名を入力してください。")
                else:
                    with service_scope() as container:
                        container.master_service.create_project(
                            user["user_id"],
                            {
                                "project_name": project_name.strip(),
                                "team_id": team["value"],
                                "color": color,
                                "display_order": int(display_order),
                                "is_active": is_active,
                            },
                        )
                    st.session_state["show_project_create"] = False
                    st.success("プロジェクトを追加しました。")
                    st.rerun()

    header = st.columns([2.1, 1.3, 1.0, 0.9, 0.9, 0.8])
    labels = ["プロジェクト", "チーム", "色", "表示順", "状態", "操作"]
    for col, label in zip(header, labels):
        col.markdown(f"**{label}**")

    for row in project_rows:
        cols = st.columns([2.1, 1.3, 1.0, 0.9, 0.9, 0.8])
        cols[0].write(row["project_name"])
        cols[1].write(row["team_name"])
        cols[2].markdown(color_chip(row["color"]), unsafe_allow_html=True)
        cols[3].caption(f"順序 {row['display_order']}")
        cols[4].markdown(
            badge("有効", "#16A34A") if row["is_active"] else badge("無効", "#6B7280"),
            unsafe_allow_html=True,
        )
        if cols[5].button("編集", key=f"edit_project_{row['project_id']}"):
            st.session_state["editing_project_id"] = row["project_id"]
            st.session_state["show_project_create"] = False
            st.rerun()

    editing_project_id = st.session_state.get("editing_project_id")
    if editing_project_id and editing_project_id in project_map:
        current = project_map[editing_project_id]
        with st.expander(f"プロジェクト編集中: {current['project_name']}", expanded=True):
            with st.form("edit_project_form"):
                project_name = st.text_input("プロジェクト名", value=current["project_name"])
                row1 = st.columns(3)
                team = row1[0].selectbox(
                    "チーム",
                    options=team_options,
                    index=next((idx for idx, item in enumerate(team_options) if item["value"] == current["team_id"]), 0),
                    format_func=lambda x: x["label"],
                )
                color = row1[1].color_picker("色", value=current["color"])
                display_order = row1[2].number_input("表示順", min_value=0, step=10, value=int(current["display_order"]))
                is_active = st.checkbox("有効", value=current["is_active"])
                action = st.columns(2)
                save_edit = action[0].form_submit_button("更新する", type="primary")
                close_edit = action[1].form_submit_button("閉じる")
                if close_edit:
                    st.session_state.pop("editing_project_id", None)
                    st.rerun()
                if save_edit:
                    if not project_name.strip():
                        st.warning("プロジェクト名を入力してください。")
                    else:
                        with service_scope() as container:
                            container.master_service.update_project(
                                editing_project_id,
                                user["user_id"],
                                {
                                    "project_name": project_name.strip(),
                                    "team_id": team["value"],
                                    "color": color,
                                    "display_order": int(display_order),
                                    "is_active": is_active,
                                },
                            )
                        st.session_state.pop("editing_project_id", None)
                        st.success("プロジェクトを更新しました。")
                        st.rerun()

st.header("応答率マスタ")
st.caption("CDR取込（応答率エンジン）が参照するマスタです。削除はせず、有効/無効で管理します。")

# --- 除外番号 (exclude_numbers) ---
st.subheader("除外番号（テストコール等）")
with st.container(border=True):
    with st.form("create_exclude_form", clear_on_submit=True):
        cols = st.columns([1.4, 2.0, 0.8])
        new_number = cols[0].text_input("発信者番号")
        new_reason = cols[1].text_input("理由")
        add_exclude = cols[2].form_submit_button("追加", type="primary")
        if add_exclude:
            if not new_number.strip():
                st.warning("発信者番号を入力してください。")
            else:
                with service_scope() as container:
                    container.answer_rate_master_service.create_exclude_number(
                        user["user_id"], new_number, new_reason
                    )
                st.success("除外番号を追加しました。")
                st.rerun()

    header = st.columns([1.4, 2.4, 0.8, 0.9])
    for col, label in zip(header, ["発信者番号", "理由", "状態", "操作"]):
        col.markdown(f"**{label}**")
    for row in exclude_rows:
        cols = st.columns([1.4, 2.4, 0.8, 0.9])
        cols[0].write(row["caller_number"])
        cols[1].caption(row["reason"] or "-")
        cols[2].markdown(
            badge("有効", "#16A34A") if row["is_active"] else badge("無効", "#6B7280"),
            unsafe_allow_html=True,
        )
        if cols[3].button("有効/無効", key=f"toggle_exclude_{row['id']}"):
            with service_scope() as container:
                container.answer_rate_master_service.toggle_exclude_number(user["user_id"], row["id"])
            st.rerun()

# --- 放棄閾値 (abandon_rules) ---
st.subheader("放棄閾値（秒数ルール）")
with st.container(border=True):
    st.caption("スキルグループ空欄＝全体既定。スキルグループ指定＝その値で上書きします。")
    with st.form("create_abandon_form", clear_on_submit=True):
        cols = st.columns([2.0, 1.2, 0.8])
        new_sg = cols[0].text_input("スキルグループ（空欄=全体既定）")
        new_threshold = cols[1].number_input("閾値秒数", min_value=0, step=1, value=0)
        add_abandon = cols[2].form_submit_button("追加", type="primary")
        if add_abandon:
            with service_scope() as container:
                container.answer_rate_master_service.create_abandon_rule(
                    user["user_id"], new_sg, int(new_threshold)
                )
            st.success("閾値ルールを追加しました。")
            st.rerun()

    header = st.columns([2.2, 1.0, 0.8, 0.9])
    for col, label in zip(header, ["スキルグループ", "閾値秒", "状態", "操作"]):
        col.markdown(f"**{label}**")
    for row in abandon_rows:
        cols = st.columns([2.2, 1.0, 0.8, 0.9])
        cols[0].write(row["skill_group"])
        cols[1].write(f"{row['threshold_seconds']} 秒")
        cols[2].markdown(
            badge("有効", "#16A34A") if row["is_active"] else badge("無効", "#6B7280"),
            unsafe_allow_html=True,
        )
        if cols[3].button("有効/無効", key=f"toggle_abandon_{row['id']}"):
            with service_scope() as container:
                container.answer_rate_master_service.toggle_abandon_rule(user["user_id"], row["id"])
            st.rerun()

# --- 合算定義 (skill_group_merge) ---
st.subheader("合算定義（業務グループ＝スキルグループ束ね）")
with st.container(border=True):
    st.caption(
        "業務グループ（親ラベル）に、配下の子スキルグループ（回線）を複数まとめて登録します。"
        "応答率閲覧タブはこの業務グループ単位で集計します。合算値は保存せず表示時に都度計算します。"
    )

    # 一括登録: 親ラベル + 子スキルグループ複数選択（候補が無ければ手入力にフォールバック）
    with st.form("create_merge_bulk_form", clear_on_submit=True):
        new_label = st.text_input("業務グループ名（親ラベル）", placeholder="例: 弁護士グループ")
        if skill_group_options:
            new_children = st.multiselect(
                f"子スキルグループ（回線）を選択　全 {len(skill_group_options)} 件（入力して検索できます）",
                options=skill_group_options,
            )
            children_text = ""
        else:
            st.caption("取込済みデータが無いため候補を表示できません。1行に1回線ずつ入力してください。")
            new_children = []
            children_text = st.text_area("子スキルグループ（1行に1件）", height=120)
        add_merge = st.form_submit_button("この業務グループに一括登録", type="primary")
        if add_merge:
            children = list(new_children) + [
                line.strip() for line in children_text.splitlines() if line.strip()
            ]
            try:
                with service_scope() as container:
                    res = container.answer_rate_master_service.create_skill_group_merge_bulk(
                        user["user_id"], new_label, children
                    )
            except ValueError as exc:
                st.warning(str(exc))
            else:
                st.success(
                    f"業務グループ『{res['label']}』に {res['added']} 件登録しました"
                    f"（重複スキップ {res['skipped']} 件）。"
                )
                st.rerun()

    # 登録済み一覧は件数が多くなる（数百件）ため初期表示しない。expander内に dataframe で格納。
    # 有効/無効管理は壊さず、行ボタンの大量描画を避けて選択式（コンパクト）で切替える。
    st.markdown(f"**登録済み業務グループ**（{len(merge_rows)} 件）")
    with st.expander("登録済み業務グループ一覧を表示", expanded=False):
        if merge_rows:
            st.dataframe(
                [
                    {
                        "親ラベル": r["merge_label"],
                        "子スキルグループ": r["child_skill_group"],
                        "状態": "有効" if r["is_active"] else "無効",
                    }
                    for r in merge_rows
                ],
                use_container_width=True,
                hide_index=True,
            )
            merge_by_id = {r["id"]: r for r in merge_rows}
            st.caption("有効/無効を切り替える定義を選んで実行してください。")
            tc1, tc2 = st.columns([3.0, 1.0])
            toggle_id = tc1.selectbox(
                "対象の業務グループ定義",
                options=[r["id"] for r in merge_rows],
                format_func=lambda i: (
                    f"{merge_by_id[i]['merge_label']} ／ {merge_by_id[i]['child_skill_group']}"
                    f"（{'有効' if merge_by_id[i]['is_active'] else '無効'}）"
                ),
                key="merge_toggle_select",
            )
            if tc2.button("有効/無効を切替", key="merge_toggle_btn"):
                with service_scope() as container:
                    container.answer_rate_master_service.toggle_skill_group_merge(
                        user["user_id"], toggle_id
                    )
                st.rerun()
        else:
            st.caption("まだ業務グループ定義がありません。")

# --- 業務グループ編集（既存グループの配下回線を追加・除外） ---
st.subheader("業務グループ編集（配下回線の追加・除外）")
with st.container(border=True):
    st.caption(
        "既存の業務グループを選び、配下の回線だけを見ながら追加・除外します。"
        "外す操作は物理削除せず is_active=0 にします（DBからは消えません）。"
    )

    ge_filter = st.text_input("業務グループ名で絞り込み", key="ge_label_filter", placeholder="例: 弁護士")
    with service_scope() as container:
        ge_labels = container.answer_rate_master_service.list_merge_labels(ge_filter)

    if not ge_labels:
        st.info("該当する業務グループがありません。『合算定義』または『業務グループ候補』から登録してください。")
    else:
        ge_label = st.selectbox(
            f"編集する業務グループ（{len(ge_labels)} 件中）",
            options=ge_labels,
            key="ge_label_select",
        )
        ge_incl_inactive = st.checkbox("無効行も表示", value=False, key="ge_incl_inactive")

        with service_scope() as container:
            ge_children = container.answer_rate_master_service.get_skill_group_merge_children(
                ge_label, include_inactive=ge_incl_inactive
            )
        active_count = sum(1 for r in ge_children if r["is_active"])
        st.markdown(f"**現在の登録回線**：有効 {active_count} 件 / 表示 {len(ge_children)} 件")

        # --- 現在の登録回線（外すチェック付き） ---
        if ge_children:
            remove_df = pd.DataFrame(
                [
                    {
                        "外す": False,
                        "child_skill_group": r["child_skill_group"],
                        "is_active": r["is_active"],
                        "created_at": r["created_at"],
                        "updated_at": r["updated_at"],
                    }
                    for r in ge_children
                ]
            )
            edited_remove = st.data_editor(
                remove_df,
                use_container_width=True,
                hide_index=True,
                disabled=["child_skill_group", "is_active", "created_at", "updated_at"],
                column_config={"外す": st.column_config.CheckboxColumn("外す", help="このグループから外す回線")},
                key="ge_remove_editor",
            )
            to_remove = [
                row["child_skill_group"]
                for _, row in edited_remove.iterrows()
                if bool(row["外す"]) and bool(row["is_active"])
            ]
            if st.button(
                f"選択した回線をこのグループから外す（{len(to_remove)} 件）",
                key="ge_remove_btn",
                disabled=not to_remove,
            ):
                with service_scope() as container:
                    n = container.answer_rate_master_service.deactivate_child_skill_groups_from_merge(
                        user["user_id"], ge_label, to_remove
                    )
                st.success(f"{n} 件をグループ『{ge_label}』から外しました（is_active=0／物理削除なし）。")
                st.rerun()
        else:
            st.caption("このグループには表示できる回線がありません（無効行は『無効行も表示』で確認できます）。")

        st.divider()

        # --- 回線追加（検索して候補から選ぶ。全件ドロップダウンは使わない） ---
        st.markdown("**回線を追加**")
        ge_add_kw = st.text_input("追加する回線を検索（キーワード）", key="ge_add_kw", placeholder="例: 弁護士ドットコム 横浜")
        ge_only_unreg = st.checkbox(
            "このグループに未登録の回線だけ表示", value=True, key="ge_only_unreg"
        )
        if not ge_add_kw.strip():
            st.caption("キーワードを入力すると、一致する回線（最大100件）を候補表示します。")
        else:
            with service_scope() as container:
                ge_cands = container.answer_rate_master_service.search_child_skill_groups(
                    skill_group_options, ge_add_kw, ge_label, only_unregistered=ge_only_unreg, limit=100
                )
            if not ge_cands:
                st.info("一致する追加候補がありません（既に有効登録済みか、キーワード不一致）。")
            else:
                st.caption(f"追加候補 {len(ge_cands)} 件（最大100件まで表示）")
                add_df = pd.DataFrame(
                    [
                        {
                            "追加": False,
                            "child_skill_group": r["child_skill_group"],
                            "状態": "無効で存在（追加で再有効化）" if r["already_inactive"] else "未登録",
                        }
                        for r in ge_cands
                    ]
                )
                edited_add = st.data_editor(
                    add_df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["child_skill_group", "状態"],
                    column_config={"追加": st.column_config.CheckboxColumn("追加", help="このグループに追加する回線")},
                    key="ge_add_editor",
                )
                to_add = [
                    row["child_skill_group"]
                    for _, row in edited_add.iterrows()
                    if bool(row["追加"])
                ]
                if st.button(
                    f"選択した回線をこのグループに追加（{len(to_add)} 件）",
                    type="primary",
                    key="ge_add_btn",
                    disabled=not to_add,
                ):
                    with service_scope() as container:
                        res = container.answer_rate_master_service.add_child_skill_groups_to_merge(
                            user["user_id"], ge_label, to_add
                        )
                    st.success(
                        f"グループ『{res['label']}』へ 新規追加 {res['added']} 件 / "
                        f"再有効化 {res['reactivated']} 件 / 重複スキップ {res['skipped']} 件。"
                    )
                    st.rerun()

# --- 業務グループ定義のバックアップ（エクスポート / インポート） ---
st.subheader("業務グループ定義のバックアップ（CSVエクスポート / インポート）")
with st.container(border=True):
    st.warning(
        "このデータはローカルDBに保存されます。Gitには保存されないため、定期的にCSVエクスポートしてください。"
    )

    # --- エクスポート ---
    with service_scope() as container:
        export_rows = container.answer_rate_master_service.export_skill_group_merge_rows()
    st.markdown("**エクスポート**")
    st.caption(f"現在の登録: {len(export_rows)} 件（merge_label / child_skill_group / is_active / created_at / updated_at）")
    if export_rows:
        export_df = pd.DataFrame(
            export_rows,
            columns=["merge_label", "child_skill_group", "is_active", "created_at", "updated_at"],
        )
        export_csv = export_df.to_csv(index=False).encode("utf-8-sig")  # Excelで開きやすいBOM付き
        st.download_button(
            "業務グループ定義をCSVダウンロード",
            data=export_csv,
            file_name="skill_group_merge_backup.csv",
            mime="text/csv",
            key="merge_export_dl",
        )
    else:
        st.info("エクスポートできる業務グループ定義がありません。")

    st.divider()

    # --- インポート ---
    st.markdown("**インポート**（追加・重複スキップ方式。既存データの削除・全置換はしません）")
    st.caption(
        "必須列: merge_label, child_skill_group（任意列: is_active）。"
        "既存の同一ペア（merge_label + child_skill_group）は重複登録しません。"
    )
    REQUIRED_COLS = ["merge_label", "child_skill_group"]
    uploaded_merge = st.file_uploader("インポートCSV", type=["csv"], key="merge_import_uploader")

    if uploaded_merge is not None:
        raw = uploaded_merge.getvalue()
        import_df = None
        read_error = None
        for enc in ("utf-8-sig", "cp932"):
            try:
                import_df = pd.read_csv(io.BytesIO(raw), encoding=enc, dtype=str).fillna("")
                break
            except Exception as exc:  # 次の候補へフォールバック
                read_error = exc
        if import_df is None:
            st.error(f"CSVを読み込めませんでした: {read_error}")
        elif not set(REQUIRED_COLS).issubset(set(import_df.columns)):
            missing = [c for c in REQUIRED_COLS if c not in import_df.columns]
            st.error(f"必須列が不足しています: {', '.join(missing)}（保存していません）")
        else:
            preview_cols = [c for c in ["merge_label", "child_skill_group", "is_active"] if c in import_df.columns]
            st.caption(f"読込プレビュー（{len(import_df)} 行）")
            st.dataframe(import_df[preview_cols], use_container_width=True, hide_index=True)

            if st.button("インポート実行", type="primary", key="merge_import_run"):
                rows = import_df.to_dict(orient="records")
                try:
                    with service_scope() as container:
                        res = container.answer_rate_master_service.import_skill_group_merge_rows(
                            user["user_id"], rows
                        )
                except Exception as exc:  # 例外は握りつぶさず表示
                    st.error(f"インポートに失敗しました: {exc}")
                else:
                    st.success(
                        f"インポート完了: 読込 {res['read']} 件 / 追加 {res['added']} 件 / "
                        f"スキップ(重複) {res['skipped']} 件 / エラー {res['errors']} 件"
                    )
                    if res["error_details"]:
                        with st.expander(f"エラー詳細（{len(res['error_details'])} 件）", expanded=False):
                            for msg in res["error_details"]:
                                st.write(f"- {msg}")
                    st.rerun()

# --- 業務グループ候補（自動抽出 → 人間確認 → 一括登録） ---
st.subheader("業務グループ候補（取込済み回線から自動抽出）")
with st.container(border=True):
    st.caption(
        "取込済みの skill_group をキーワードでまとめた候補を表示します。"
        "自動登録はしません。内容を確認し、候補ごとに『この候補を登録』を押すと skill_group_merge に登録します。"
    )

    if not skill_group_options:
        st.info("取込済みの回線データがありません。『応答率速報』のCDR取込後に候補を抽出できます。")
    else:
        default_kw_text = "、".join(DEFAULT_GROUP_CANDIDATE_KEYWORDS)
        kw_text = st.text_area(
            "キーワード（読点・改点・カンマ区切り。初期値は編集できます。保存はされません）",
            value=default_kw_text,
            height=80,
            key="group_candidate_keywords",
        )
        import re as _re  # 区切り文字（読点/カンマ/改行/中点）で分割
        keywords = [k.strip() for k in _re.split(r"[、,\n・]+", kw_text) if k.strip()]

        with service_scope() as container:
            candidates = container.answer_rate_master_service.build_group_candidates(
                skill_group_options, keywords
            )

        if not candidates:
            st.info("キーワードに一致する回線がありませんでした。キーワードを見直してください。")
        else:
            st.caption(f"候補 {len(candidates)} 件（キーワードを含む回線をまとめています）")

        def render_group_candidate(cand: dict, key_id: str, caption_suffix: str = "",
                                   nested: bool = False) -> None:
            """候補1件を描画（名前編集・件数・一覧・登録ボタン）。分割候補にも再利用する。

            nested=True（親expander内＝分割候補）のときは、expanderを入れ子にできないため
            一覧はチェックボックスで表示切替する（要件: 各分割候補の一覧を確認できる）。
            """
            head = st.columns([2.2, 1.0])
            edited_label = head[0].text_input(
                "候補グループ名（登録前に編集可）",
                value=cand["label"],
                key=f"cand_label_{key_id}",
            )
            if cand["fully_registered"]:
                head[1].markdown(badge("登録済み", "#16A34A"), unsafe_allow_html=True)
            else:
                head[1].markdown(
                    badge(f"未登録 {cand['unregistered_count']}件", "#D97706"),
                    unsafe_allow_html=True,
                )
            st.caption(
                f"対象回線数: {cand['line_count']} 件 ／ "
                f"登録済み {cand['registered_count']} 件 ／ 未登録 {cand['unregistered_count']} 件{caption_suffix}"
            )
            lines_view = [{"回線(skill_group)": line} for line in cand["lines"]]
            if nested:
                if st.checkbox(
                    f"対象回線一覧（{cand['line_count']} 件）を表示", key=f"cand_list_{key_id}"
                ):
                    st.dataframe(lines_view, use_container_width=True, hide_index=True)
            else:
                with st.expander(f"対象回線一覧（{cand['line_count']} 件）を確認", expanded=False):
                    st.dataframe(lines_view, use_container_width=True, hide_index=True)
            if st.button(
                "この候補を登録",
                key=f"cand_reg_{key_id}",
                type="primary",
                disabled=cand["fully_registered"],
            ):
                try:
                    with service_scope() as container:
                        res = container.answer_rate_master_service.create_skill_group_merge_bulk(
                            user["user_id"], edited_label, cand["lines"]
                        )
                except ValueError as exc:
                    st.warning(str(exc))
                else:
                    st.success(
                        f"業務グループ『{res['label']}』に {res['added']} 件登録しました"
                        f"（重複スキップ {res['skipped']} 件）。"
                    )
                    st.rerun()

        for cand in candidates:
            kw = cand["keyword"]
            with st.container(border=True):
                render_group_candidate(cand, kw, caption_suffix=f"（キーワード『{kw}』）")

                # 対象回線数が多い候補だけ、地域名での分割候補を提示（初期は閉じる）。
                if cand["line_count"] >= SPLIT_SUGGEST_MIN_LINES:
                    with st.expander(
                        f"分割候補を表示（{cand['line_count']} 件と大きいため地域別に分割）",
                        expanded=False,
                    ):
                        st.caption(
                            "地域名で分割した候補です。完全自動分類ではないため、内容を確認してから登録してください。"
                            "複数地域を含む場合は最初に一致した地域に入ります。どれにも当たらない回線は『未分類』です。"
                        )
                        region_text = st.text_area(
                            "地域名（読点・カンマ・改行区切り。編集可。保存はされません）",
                            value="、".join(DEFAULT_REGION_KEYWORDS),
                            height=70,
                            key=f"split_regions_{kw}",
                        )
                        region_keywords = [
                            r.strip() for r in _re.split(r"[、,\n・]+", region_text) if r.strip()
                        ]
                        with service_scope() as container:
                            split_candidates = container.answer_rate_master_service.build_split_group_candidates(
                                cand, region_keywords
                            )
                        if not split_candidates:
                            st.info("分割候補がありません。")
                        for sc in split_candidates:
                            with st.container(border=True):
                                render_group_candidate(
                                    sc,
                                    f"{kw}__{sc['region']}",
                                    caption_suffix=f"（地域: {sc['region']}）",
                                    nested=True,
                                )

# --- オペレーター (operators) ---
st.subheader("オペレーター")
with st.container(border=True):
    st.caption("OP/オペレーターのマスタです（アプリ利用者=User とは別物）。")
    with st.form("create_operator_form", clear_on_submit=True):
        cols = st.columns([1.0, 1.4, 1.4, 1.0, 0.7])
        op_code = cols[0].text_input("OPコード")
        op_name = cols[1].text_input("表示名")
        op_sg = cols[2].text_input("スキルグループ")
        op_shift = cols[3].text_input("シフト種別（任意）")
        add_op = cols[4].form_submit_button("追加", type="primary")
        if add_op:
            if not op_code.strip() or not op_name.strip():
                st.warning("OPコードと表示名を入力してください。")
            else:
                try:
                    with service_scope() as container:
                        container.answer_rate_master_service.create_operator(
                            user["user_id"], op_code, op_name, op_sg, op_shift
                        )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("オペレーターを追加しました。")
                    st.rerun()

    header = st.columns([1.0, 1.4, 1.4, 1.0, 0.8, 0.9])
    for col, label in zip(header, ["OPコード", "表示名", "スキルグループ", "シフト", "状態", "操作"]):
        col.markdown(f"**{label}**")
    for row in operator_rows:
        cols = st.columns([1.0, 1.4, 1.4, 1.0, 0.8, 0.9])
        cols[0].write(row["op_code"])
        cols[1].write(row["display_name"])
        cols[2].caption(row["skill_group"] or "-")
        cols[3].caption(row["shift_type"] or "-")
        cols[4].markdown(
            badge("有効", "#16A34A") if row["status"] == "active" else badge("無効", "#6B7280"),
            unsafe_allow_html=True,
        )
        if cols[5].button("有効/無効", key=f"toggle_op_{row['id']}"):
            with service_scope() as container:
                container.answer_rate_master_service.toggle_operator(user["user_id"], row["id"])
            st.rerun()

st.subheader("アプリ一覧")
st.dataframe(apps, use_container_width=True, hide_index=True)

st.subheader("監査ログ")
st.dataframe(audit_logs, use_container_width=True, hide_index=True)

st.subheader("応答率速報履歴")
st.dataframe(response_history, use_container_width=True, hide_index=True)
