"""応答率エンジン（決定論・AI不使用）。

通話呼詳細CSVの DataFrame を入力に、raw skill_group 単位で
(日付, 時間帯, スキルグループ) ごとの完了呼数・有効放棄呼数を集計する。

確定済み定義:
    応答率 = 完了呼 / (完了呼 + 有効放棄呼)

前処理は順序厳守:
    1. 発信呼=1 を全除外（着信のみ対象）
    2. テスト除外（発信者番号が exclude_numbers に載るものを除外）
    3. 呼損判定: 呼損 = 放棄呼=1 のみ。完了でも放棄でもない呼は分母にも分子にも入れない。
    4. 秒数ルール: 放棄呼のうち (切断時間 - 着信時間) の経過秒 <= 閾値 のものは呼損に数えない。

合算（skill_group_merge）は call_stats に保存せず、表示・報告時に都度計算する。

判定ロジックにAIは一切使わない。AIは文面生成・要約補助のみ（本モジュールでは未使用）。
"""
import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

# import_log.engine_version に保存する。集計定義を変えたら必ず上げること。
ENGINE_VERSION = "answer_rate_v1"

# 固定マッピング初期値（UIで上書き可能）。論理キー -> CSV列名。
DEFAULT_COLUMN_MAPPING = {
    "skill_group": "スキルグループ",
    "inbound_time": "着信時間",
    "disconnect_time": "切断時間",
    "completed": "完了呼",
    "abandoned": "放棄呼",
    "outbound": "発信呼",
    "caller_number": "発信者番号",
}

REQUIRED_FIELDS = list(DEFAULT_COLUMN_MAPPING.keys())

# 経過秒の近似に関する注記。import_log.definition_note とコード両方に必ず残す。
ELAPSED_APPROX_NOTE = (
    "放棄呼の経過秒は専用の『呼出時間』列が無いため、着信時間→切断時間の総経過秒で代用した近似値である。"
    "これは厳密な呼出秒数ではなく呼の総経過秒であり、秒数ルール（閾値以下は呼損に数えない）に用いている。"
)


def answer_rate(completed_count: int, valid_abandon_count: int) -> float:
    """応答率(%) = 完了呼 / (完了呼 + 有効放棄呼)。分母0は0.0。"""
    denominator = completed_count + valid_abandon_count
    if denominator == 0:
        return 0.0
    rate = Decimal(int(completed_count) * 100) / Decimal(int(denominator))
    return float(rate.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def build_threshold_rules(abandon_rules) -> dict:
    """abandon_rules（有効行のみ）から閾値ルールを組み立てる。

    skill_group が None の行 = 全体既定。指定行 = スキルグループ別上書き。
    戻り値は import_log.threshold_rule_snapshot_json にそのまま保存できる形。
    """
    default_seconds = 0
    by_skill: dict[str, int] = {}
    for rule in abandon_rules:
        if not getattr(rule, "is_active", True):
            continue
        if rule.skill_group is None or str(rule.skill_group).strip() == "":
            default_seconds = int(rule.threshold_seconds)
        else:
            by_skill[str(rule.skill_group)] = int(rule.threshold_seconds)
    return {
        "engine_version": ENGINE_VERSION,
        "default_seconds": default_seconds,
        "by_skill": by_skill,
        "definition_note": ELAPSED_APPROX_NOTE,
    }


def threshold_for(skill_group: str, threshold_rules: dict) -> int:
    return int(threshold_rules.get("by_skill", {}).get(str(skill_group), threshold_rules.get("default_seconds", 0)))


def exclude_set_and_hash(exclude_numbers) -> tuple[set, str]:
    """有効な除外発信者番号の集合と、取込時点を追跡するためのスナップショットhashを返す。"""
    numbers = sorted({str(x.caller_number).strip() for x in exclude_numbers if getattr(x, "is_active", True)})
    snapshot = json.dumps(numbers, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(snapshot.encode("utf-8")).hexdigest()
    return set(numbers), digest


def validate_mapping(df_columns, mapping: dict) -> list[str]:
    """必須列チェック。マッピング先の列がCSVに存在しないものを返す。"""
    cols = set(df_columns)
    return [logical for logical, actual in mapping.items() if actual not in cols]


def aggregate(df: pd.DataFrame, mapping: dict, threshold_rules: dict, exclude_set: set) -> dict:
    """前処理（順序厳守）を適用し、raw skill_group 単位で集計する。

    戻り値:
        {
          "stats": [ {stat_date, time_slot, skill_group, completed_count, valid_abandon_count}, ... ],
          "summary": {...検証・件数サマリ...},
        }
    """
    m = mapping
    work = pd.DataFrame(
        {
            "skill_group": df[m["skill_group"]].astype(str),
            "caller_number": df[m["caller_number"]].astype(str).str.strip(),
            "completed": pd.to_numeric(df[m["completed"]], errors="coerce").fillna(0).astype(int),
            "abandoned": pd.to_numeric(df[m["abandoned"]], errors="coerce").fillna(0).astype(int),
            "outbound": pd.to_numeric(df[m["outbound"]], errors="coerce").fillna(0).astype(int),
            "inbound_time": pd.to_datetime(df[m["inbound_time"]], errors="coerce"),
            "disconnect_time": pd.to_datetime(df[m["disconnect_time"]], errors="coerce"),
        }
    )
    total_rows = len(work)

    # 1. 発信呼=1 を全除外（着信のみ対象）
    outbound_dropped = int((work["outbound"] == 1).sum())
    work = work[work["outbound"] != 1]

    # 2. テスト除外（発信者番号が exclude_numbers に載るものを除外）
    excluded_dropped = 0
    if exclude_set:
        mask = work["caller_number"].isin(exclude_set)
        excluded_dropped = int(mask.sum())
        work = work[~mask]

    # 着信時間が解釈できない行は集計軸（日・時）が定まらないため除外し、件数を記録
    invalid_inbound = int(work["inbound_time"].isna().sum())
    work = work[work["inbound_time"].notna()].copy()

    work["stat_date"] = work["inbound_time"].dt.date
    work["time_slot"] = work["inbound_time"].dt.hour  # 着信時間の「時」(0-23)

    # 経過秒 = 切断時間 - 着信時間（呼出秒数の近似。ELAPSED_APPROX_NOTE 参照）
    work["elapsed_sec"] = (work["disconnect_time"] - work["inbound_time"]).dt.total_seconds()
    negative_elapsed = int((work["elapsed_sec"] < 0).sum())  # 切断<着信は妥当性異常候補

    work["threshold"] = work["skill_group"].map(lambda sg: threshold_for(sg, threshold_rules))

    # 3. 呼損判定: 呼損 = 放棄呼=1 のみ。完了でも放棄でもない呼は分母/分子に入れない。
    # 4. 秒数ルール: 放棄呼のうち経過秒 <= 閾値 は呼損に数えない（= 経過秒 > 閾値 のみ有効放棄）。
    work["is_completed"] = work["completed"] == 1
    work["is_valid_abandon"] = (work["abandoned"] == 1) & (work["elapsed_sec"] > work["threshold"])

    neutral_calls = int((~work["is_completed"] & ~work["is_valid_abandon"] & (work["abandoned"] != 1)).sum())
    abandon_within_threshold = int(((work["abandoned"] == 1) & (work["elapsed_sec"] <= work["threshold"])).sum())

    grouped = (
        work.groupby(["stat_date", "time_slot", "skill_group"], dropna=False)
        .agg(
            completed_count=("is_completed", "sum"),
            valid_abandon_count=("is_valid_abandon", "sum"),
        )
        .reset_index()
    )
    # 完了も有効放棄も0のグループ（中立呼のみ）は意味を持たないため保存対象から除く
    grouped = grouped[(grouped["completed_count"] + grouped["valid_abandon_count"]) > 0]

    stats = [
        {
            "stat_date": row.stat_date,
            "time_slot": int(row.time_slot),
            "skill_group": str(row.skill_group),
            "completed_count": int(row.completed_count),
            "valid_abandon_count": int(row.valid_abandon_count),
        }
        for row in grouped.itertuples(index=False)
    ]

    completed_total = sum(s["completed_count"] for s in stats)
    valid_abandon_total = sum(s["valid_abandon_count"] for s in stats)
    summary = {
        "total_rows": total_rows,
        "outbound_dropped": outbound_dropped,
        "excluded_dropped": excluded_dropped,
        "invalid_inbound_dropped": invalid_inbound,
        "neutral_calls_ignored": neutral_calls,
        "abandon_within_threshold_ignored": abandon_within_threshold,
        "negative_elapsed_flagged": negative_elapsed,
        "completed_total": completed_total,
        "valid_abandon_total": valid_abandon_total,
        "overall_answer_rate": answer_rate(completed_total, valid_abandon_total),
        "stat_group_count": len(stats),
    }
    return {"stats": stats, "summary": summary}


# ---------------------------------------------------------------------------
# 表示・報告用の都度計算（保存しない）
# ---------------------------------------------------------------------------

def by_date(stats: list[dict]) -> list[dict]:
    return _rollup(stats, keys=("stat_date",))


def by_time_slot(stats: list[dict]) -> list[dict]:
    return _rollup(stats, keys=("stat_date", "time_slot"))


def by_skill_group(stats: list[dict]) -> list[dict]:
    return _rollup(stats, keys=("skill_group",))


def _rollup(stats: list[dict], keys: tuple) -> list[dict]:
    acc: dict[tuple, dict] = {}
    for s in stats:
        k = tuple(s[key] for key in keys)
        bucket = acc.setdefault(k, {"completed_count": 0, "valid_abandon_count": 0})
        bucket["completed_count"] += s["completed_count"]
        bucket["valid_abandon_count"] += s["valid_abandon_count"]
    rows = []
    for k, v in acc.items():
        row = {key: k[i] for i, key in enumerate(keys)}
        row["completed_count"] = v["completed_count"]
        row["valid_abandon_count"] = v["valid_abandon_count"]
        row["answer_rate"] = answer_rate(v["completed_count"], v["valid_abandon_count"])
        rows.append(row)
    return sorted(rows, key=lambda r: tuple(str(r[key]) for key in keys))


def by_merge_label(stats: list[dict], merges) -> list[dict]:
    """skill_group_merge に従い合算した応答率を都度計算する（保存しない）。

    merges: SkillGroupMerge 行、または {merge_label, child_skill_group, is_active} の dict の反復可能。
    合算定義は後から変わり得るため、保存済みの raw stats から表示時に毎回計算する。
    """
    def _field(mg, name):
        return mg[name] if isinstance(mg, dict) else getattr(mg, name)

    label_to_children: dict[str, set] = {}
    for mg in merges:
        if not _field(mg, "is_active"):
            continue
        label_to_children.setdefault(str(_field(mg, "merge_label")), set()).add(str(_field(mg, "child_skill_group")))

    rows = []
    for label, children in label_to_children.items():
        completed = sum(s["completed_count"] for s in stats if s["skill_group"] in children)
        valid_abandon = sum(s["valid_abandon_count"] for s in stats if s["skill_group"] in children)
        rows.append(
            {
                "merge_label": label,
                "children": "・".join(sorted(children)),
                "completed_count": completed,
                "valid_abandon_count": valid_abandon,
                "answer_rate": answer_rate(completed, valid_abandon),
            }
        )
    return sorted(rows, key=lambda r: r["merge_label"])


# 報告文の表示モード。集計ロジックは変えず、並べ替え・件数制限のみで実務向けに整える。
REPORT_MODES = {
    "overall": "全体サマリのみ",
    "low_rate_20": "応答率低い順20件",
    "high_count_20": "件数多い順20件",
    "all": "全件表示",
}
DEFAULT_REPORT_MODE = "overall"

# 長いスキルグループ名（弁護士ドットコム系など）は報告文・PDFで崩れるため先頭で省略する。
SKILL_GROUP_NAME_MAX = 80


def _truncate_name(name: str, limit: int = SKILL_GROUP_NAME_MAX) -> str:
    name = str(name)
    return name if len(name) <= limit else name[:limit] + "..."


def build_report_text(
    stats: list[dict],
    merges=None,
    overall: dict | None = None,
    mode: str = DEFAULT_REPORT_MODE,
) -> str:
    """決定論的なテンプレート報告文。外部AI未設定でも応答率管理は完結する。

    mode（表示切替。集計値そのものは変えず、並べ替えと件数制限だけを行う）:
        "overall"       … 全体サマリのみ（既定。スキルグループ別は出さない）
        "low_rate_20"   … 応答率が低い順に20件
        "high_count_20" … 件数（完了+有効放棄）が多い順に20件
        "all"           … 全件

    AI生成は設定済みの場合のみ任意補助として別途差し込む想定（本関数はAI不使用）。
    """
    lines: list[str] = []
    if overall is not None:
        lines.append(
            f"全体 応答率 {overall['overall_answer_rate']:.1f}%"
            f"（完了{overall['completed_total']} / 有効放棄{overall['valid_abandon_total']}）"
        )

    if mode != "overall":
        rows = by_skill_group(stats)
        if mode == "low_rate_20":
            rows = sorted(rows, key=lambda r: r["answer_rate"])[:20]
            heading = "【スキルグループ別 応答率低い順20件】"
        elif mode == "high_count_20":
            rows = sorted(
                rows,
                key=lambda r: r["completed_count"] + r["valid_abandon_count"],
                reverse=True,
            )[:20]
            heading = "【スキルグループ別 件数多い順20件】"
        else:  # "all"
            heading = "【スキルグループ別 全件】"

        lines.append("")
        lines.append(heading)
        for row in rows:
            denom = row["completed_count"] + row["valid_abandon_count"]
            name = _truncate_name(row["skill_group"])
            lines.append(f"{name}：{row['completed_count']}/{denom} {row['answer_rate']:.1f}%")

    if merges:
        merged = by_merge_label(stats, merges)
        if merged:
            lines.append("")
            lines.append("【合算ラベル別】")
            for row in merged:
                denom = row["completed_count"] + row["valid_abandon_count"]
                name = _truncate_name(row["merge_label"])
                lines.append(f"{name}：{row['completed_count']}/{denom} {row['answer_rate']:.1f}%")
    return "\n".join(lines)
