"""CT-e1自動化サービス（Phase 0確認 / CSV呼損チェックの土台）。

方針（今回の範囲）:
- CT-e1 Suite への自動ログイン・GUI自動化・非公開API・Cookie/token利用は一切しない。
- Teams本送信もしない（通知文プレビューのみ生成する）。
- 呼損量 = 放棄呼のみ。CSVの「放棄呼」列が 1 の行だけを呼損量として集計する。
  「待ち呼」「完了呼=0」「拒否」「呼出中切断」は呼損量に含めない。
  「発信呼」列がある場合、発信呼=1 の行は集計前に除外する（着信のみ対象）。
- 集計の判定ロジックにAIは使わない（決定論）。

設計:
- 集計・読込・通知文生成は副作用のない純粋関数（モジュール関数）として実装し、単体テスト可能にする。
- Phase 0確認・設定・実行ログの保存は CtE1Store（JSONファイル）に分離する。
  既存DBスキーマ・migrationは変更しない（DB保存が必要になったら別途相談する）。
- 生CSV本文の加工はPython側で文字コードを明示して行う（PowerShellで直接編集しない）。
"""
import io
import json
import os
from datetime import datetime

import pandas as pd


class CtE1Error(Exception):
    """CT-e1 CSV処理の業務エラー（必須列不足・読込失敗など）。"""


# CSV読込で順に試す文字コード（utf-8-sig → utf-8 → cp932 → shift_jis）。
ENCODINGS_TRY = ["utf-8-sig", "utf-8", "cp932", "shift_jis"]

# 必須列（不足ならエラー）。
REQUIRED_COLUMNS = ["放棄呼", "スキルグループ", "着信時間"]

# 任意列（あれば利用する）。発信呼があれば 発信呼=1 を除外する。
OPTIONAL_COLUMNS = ["SessionID", "発信呼", "待ち呼", "完了呼", "切断時間", "通話開始時間"]

OUTBOUND_COLUMN = "発信呼"
ABANDON_COLUMN = "放棄呼"
SKILL_GROUP_COLUMN = "スキルグループ"
INBOUND_TIME_COLUMN = "着信時間"


# ---------------------------------------------------------------------------
# 読込
# ---------------------------------------------------------------------------
def detect_and_read(raw: bytes) -> tuple[str, pd.DataFrame]:
    """エンコードを順に試し、(encoding, DataFrame) を返す。全て失敗で CtE1Error。

    すべての列を文字列として読み込み（数値化は集計側で明示的に行う）、生CSVは加工しない。
    """
    last_error = None
    for enc in ENCODINGS_TRY:
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=enc, dtype=str, low_memory=False)
            return enc, df
        except UnicodeDecodeError as exc:
            last_error = exc
        except Exception as exc:  # noqa: BLE001 - 壊れた行など。次の候補へフォールバック
            last_error = exc
    raise CtE1Error(f"CSVのエンコード判定・読込に失敗しました: {last_error}")


def validate_columns(df_columns) -> list[str]:
    """必須列のうちCSVに存在しないものを返す（空なら充足）。"""
    cols = set(df_columns)
    return [c for c in REQUIRED_COLUMNS if c not in cols]


def _to_int_series(series: pd.Series) -> pd.Series:
    """フラグ列を数値化する。空欄・非数値は0扱い。"""
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


# ---------------------------------------------------------------------------
# 集計（純粋関数・DB非保存）
# ---------------------------------------------------------------------------
def aggregate_call_loss(
    df: pd.DataFrame,
    threshold: int = 0,
    target_skill_groups=None,
) -> dict:
    """呼損量（放棄呼のみ）を集計する。

    前処理（順序厳守）:
        1. 発信呼列があれば 発信呼=1 を除外（着信のみ対象）。
        2. 放棄呼=1 の行だけを呼損量として数える（完了呼=0・待ち呼などは含めない）。

    引数:
        threshold: アラート判定のしきい値。スキルグループ別放棄呼数 >= threshold で対象。
        target_skill_groups: 指定があればそのスキルグループのみを集計対象に絞る（任意）。

    戻り値（list[dict]・ORM非使用）:
        {
          "total_rows": 総行数,
          "has_outbound_column": 発信呼列の有無,
          "outbound_excluded": 発信呼=1で除外した行数,
          "rows_after_exclude": 除外後の行数,
          "abandon_count": 全体の放棄呼数,
          "by_skill_group": [{skill_group, abandon_count}, ...],  # 放棄呼数の多い順
          "threshold": しきい値,
          "alerts": [{skill_group, abandon_count, threshold}, ...],  # しきい値以上のみ
        }
    """
    missing = validate_columns(df.columns)
    if missing:
        raise CtE1Error(f"必須列が見つかりません: {', '.join(missing)}")

    total_rows = len(df)
    has_outbound = OUTBOUND_COLUMN in df.columns

    work = pd.DataFrame(
        {
            "skill_group": df[SKILL_GROUP_COLUMN].astype(str),
            "abandoned": _to_int_series(df[ABANDON_COLUMN]),
        }
    )
    if has_outbound:
        work["outbound"] = _to_int_series(df[OUTBOUND_COLUMN])
    else:
        work["outbound"] = 0

    # 1. 発信呼=1 を除外（着信のみ対象）
    outbound_excluded = int((work["outbound"] == 1).sum())
    work = work[work["outbound"] != 1]

    # 対象スキルグループの絞り込み（任意）
    if target_skill_groups:
        targets = {str(x) for x in target_skill_groups}
        work = work[work["skill_group"].isin(targets)]

    rows_after_exclude = len(work)

    # 2. 呼損量 = 放棄呼=1 のみ
    is_abandon = work["abandoned"] == 1
    abandon_count = int(is_abandon.sum())

    grouped = (
        work.loc[is_abandon]
        .groupby("skill_group")
        .size()
        .reset_index(name="abandon_count")
    )
    by_skill_group = [
        {"skill_group": str(row.skill_group), "abandon_count": int(row.abandon_count)}
        for row in grouped.itertuples(index=False)
    ]
    by_skill_group.sort(key=lambda r: (-r["abandon_count"], r["skill_group"]))

    threshold = int(threshold)
    alerts = [
        {"skill_group": r["skill_group"], "abandon_count": r["abandon_count"], "threshold": threshold}
        for r in by_skill_group
        if r["abandon_count"] >= threshold
    ]

    return {
        "total_rows": total_rows,
        "has_outbound_column": has_outbound,
        "outbound_excluded": outbound_excluded,
        "rows_after_exclude": rows_after_exclude,
        "abandon_count": abandon_count,
        "by_skill_group": by_skill_group,
        "threshold": threshold,
        "alerts": alerts,
    }


# ---------------------------------------------------------------------------
# 通知文プレビュー（Teams本送信はしない・文字列を返すだけ）
# ---------------------------------------------------------------------------
def build_notification_text(result: dict, title: str = "CT-e1 呼損確認", checked_at: str | None = None) -> str:
    """集計結果から通知文プレビューを組み立てる（決定論。送信はしない）。"""
    stamp = checked_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    threshold = result.get("threshold", 0)
    lines = [
        f"【{title}】{stamp}",
        f"放棄呼（呼損量）合計: {result.get('abandon_count', 0)} 件 / しきい値: {threshold}",
    ]
    alerts = result.get("alerts") or []
    if not alerts:
        lines.append("しきい値超過なし")
        return "\n".join(lines)

    lines.append("")
    lines.append(f"■ しきい値以上のスキルグループ（{len(alerts)}件）")
    for a in alerts:
        lines.append(f"・{a['skill_group']}：放棄呼 {a['abandon_count']} 件（しきい値 {a['threshold']}）")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase 0確認項目の定義（チェックリスト/入力欄の見出し）
# ---------------------------------------------------------------------------
PHASE0_ITEMS = [
    "週次CSV出力にかかる時間",
    "月次CSV出力にかかる時間",
    "18:00呼損確認にかかる時間",
    "20:00呼損確認にかかる時間",
    "21:00呼損確認にかかる時間",
    "週次出力対象帳票名",
    "月次出力対象帳票名",
    "呼損確認に使う帳票名",
    "CSV文字コード",
    "CSV主要列",
    "加工後ファイル名ルール",
    "保存先フォルダ",
    "月別フォルダ命名ルール",
    "対象スキルグループ",
    "18:00しきい値",
    "20:00しきい値",
    "21:00しきい値",
    "Teams通知先",
    "自動実行PC",
    "Python実行可否",
    "共有フォルダ権限",
    "Teams Webhook可否",
    "CT-e1公式API有無",
    "スケジュール出力機能有無",
    "GUI自動化可否",
    "社内承認要否",
]


# ---------------------------------------------------------------------------
# 永続化（JSONファイル。既存DBスキーマは変更しない）
# ---------------------------------------------------------------------------
class CtE1Store:
    """Phase 0確認・設定・実行ログをJSONファイルで保存する軽量ストア。

    DBスキーマ追加を避けるため、まずはファイル保存とする（必要になればDB化を別途相談）。
    """

    def __init__(self, base_dir: str = "data/ct_e1"):
        self.base_dir = base_dir
        self.phase0_path = os.path.join(base_dir, "phase0.json")
        self.settings_path = os.path.join(base_dir, "settings.json")
        self.log_path = os.path.join(base_dir, "run_log.jsonl")

    def _ensure_dir(self) -> None:
        os.makedirs(self.base_dir, exist_ok=True)

    @staticmethod
    def _read_json(path: str, default):
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return default

    def _write_json(self, path: str, data) -> None:
        self._ensure_dir()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # --- Phase 0確認 ---
    def load_phase0(self) -> dict:
        return self._read_json(self.phase0_path, {})

    def save_phase0(self, values: dict) -> None:
        payload = dict(values)
        payload["_updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_json(self.phase0_path, payload)

    # --- 設定 ---
    def load_settings(self) -> dict:
        return self._read_json(self.settings_path, {})

    def save_settings(self, values: dict) -> None:
        payload = dict(values)
        payload["_updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_json(self.settings_path, payload)

    # --- 実行ログ（追記式・JSON Lines） ---
    def append_log(self, entry: dict) -> dict:
        self._ensure_dir()
        record = dict(entry)
        record.setdefault("at", datetime.now().isoformat(timespec="seconds"))
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def list_logs(self, limit: int = 200) -> list[dict]:
        if not os.path.exists(self.log_path):
            return []
        rows: list[dict] = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        rows.reverse()  # 新しい順
        return rows[:limit]
