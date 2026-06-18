"""CT-e1 呼損チェックの CLI ラッパー（保存済みCSVのバッチ処理）。

このスクリプトは「すでに保存済みのCT-e1 CSV」を読み、既存の決定論サービス
（src.services.ct_e1_service）で呼損量（放棄呼のみ）を集計し、通知文プレビューと
JSONサマリをファイル出力するだけのものです。

やらないこと（方針・厳守）:
- CT-e1 Suite への自動ログイン・GUI自動化・非公開API・Cookie/token利用は一切しない。
- Teams本送信はしない（通知文プレビューを生成・保存・標準出力するだけ）。
- DBスキーマは変更しない（実行ログは既存 CtE1Store のJSON Lines追記のみ）。
- Windows Task Scheduler への登録はしない（手動実行・将来のスケジューリングは docs を参照）。
- 生CSV本文は出力・保存しない（集計サマリと通知文のみ保存）。

使い方（リポジトリ直下から）:
    python scripts/run_ct_e1_call_loss_check.py
        data/ct_e1/inbox/ の最新 *.csv を mtime で選び処理する。
    python scripts/run_ct_e1_call_loss_check.py --csv path/to/file.csv
        明示したCSVを処理する（inbox選択より優先）。

終了コード:
    0 成功
    1 CSVが見つからない
    2 CSV読込 / 必須列 / 業務エラー
    3 予期しないエラー
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# このスクリプトを `python scripts/run_ct_e1_call_loss_check.py` のように直接実行すると
# sys.path[0] は scripts/ になり `src` パッケージが見つからない。リポジトリ直下を先頭に追加する。
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.services import ct_e1_service as cte  # noqa: E402  (sys.path調整の後に読み込む)

# 既定パス（リポジトリ直下からの相対。.gitignore が data/ct_e1/ を除外している）。
DEFAULT_DATA_DIR = "data/ct_e1"
DEFAULT_INBOX = "data/ct_e1/inbox"
DEFAULT_OUTBOX = "data/ct_e1/outbox"

# 出力ファイル名のプレフィックス。
OUTPUT_PREFIX = "ct_e1_call_loss"


# ---------------------------------------------------------------------------
# 引数解析
# ---------------------------------------------------------------------------
def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_ct_e1_call_loss_check",
        description="保存済みCT-e1 CSVの呼損チェック（放棄呼のみ集計・通知文プレビュー生成）。",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="処理する単一CSVを明示指定する（inboxの最新選択より優先）。",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=None,
        help="しきい値の上書き（未指定なら設定値、なければ0）。",
    )
    parser.add_argument(
        "--target-skill-group",
        action="append",
        default=None,
        dest="target_skill_group",
        help="対象スキルグループ（繰り返し指定可。指定時は設定値を上書き）。",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="実行ログ（run_log.jsonl）への追記を行わない。",
    )
    parser.add_argument(
        "--inbox",
        default=DEFAULT_INBOX,
        help=f"入力CSVフォルダ（既定: {DEFAULT_INBOX}）。",
    )
    parser.add_argument(
        "--outbox",
        default=DEFAULT_OUTBOX,
        help=f"出力フォルダ（既定: {DEFAULT_OUTBOX}）。",
    )
    parser.add_argument(
        "--data-dir",
        default=DEFAULT_DATA_DIR,
        help=f"CtE1Store のベースフォルダ（設定/実行ログ。既定: {DEFAULT_DATA_DIR}）。",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# 入力選択（決定論）
# ---------------------------------------------------------------------------
def find_latest_csv(inbox: Path) -> Path | None:
    """inbox 内の最新 *.csv を返す。mtime降順、同点はファイル名で決定論的に選ぶ。"""
    if not inbox.exists() or not inbox.is_dir():
        return None
    candidates = [p for p in inbox.glob("*.csv") if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.stat().st_mtime, p.name))


# ---------------------------------------------------------------------------
# 設定の解決（CLI上書き > 設定 > 既定）
# ---------------------------------------------------------------------------
def resolve_threshold(cli_threshold, settings: dict) -> int:
    if cli_threshold is not None:
        return int(cli_threshold)
    try:
        return int(settings.get("threshold", 0) or 0)
    except (TypeError, ValueError):
        return 0


def resolve_target_skill_groups(cli_groups, settings: dict):
    """対象スキルグループを解決する。空なら None（全グループ対象）。

    CLI（--target-skill-group の繰り返し）が指定されていればそれを優先する。
    なければ設定値（改行区切り文字列、または配列）を解釈する。
    """
    if cli_groups:
        groups = [str(g).strip() for g in cli_groups if str(g).strip()]
        return groups or None
    raw = settings.get("target_skill_groups") or ""
    if isinstance(raw, str):
        groups = [s.strip() for s in raw.splitlines() if s.strip()]
    elif isinstance(raw, (list, tuple)):
        groups = [str(s).strip() for s in raw if str(s).strip()]
    else:
        groups = []
    return groups or None


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------
def write_outputs(outbox: Path, stamp: str, text: str, payload: dict) -> tuple[Path, Path]:
    """通知文(.txt)と集計サマリ(.json)を outbox に書き出す。生CSVは保存しない。"""
    outbox.mkdir(parents=True, exist_ok=True)
    txt_path = outbox / f"{OUTPUT_PREFIX}_{stamp}.txt"
    json_path = outbox / f"{OUTPUT_PREFIX}_{stamp}.json"
    txt_path.write_text(text, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return txt_path, json_path


# ---------------------------------------------------------------------------
# オーケストレーション（テスト可能。副作用は出力ファイルと任意のログ追記のみ）
# ---------------------------------------------------------------------------
def process_csv(
    csv_path: Path,
    *,
    store: "cte.CtE1Store",
    threshold: int,
    target_skill_groups,
    outbox: Path,
    write_log: bool,
    now: datetime | None = None,
) -> dict:
    """CSVを読み込み、集計・通知文生成・出力・（任意で）ログ追記まで行う。

    読込/必須列/業務エラーは cte.CtE1Error として送出される（呼び出し側で終了コード2に対応）。
    """
    raw = csv_path.read_bytes()
    encoding, df = cte.detect_and_read(raw)  # 失敗時 CtE1Error
    missing = cte.validate_columns(df.columns)
    if missing:
        raise cte.CtE1Error(f"必須列が見つかりません: {', '.join(missing)}")

    result = cte.aggregate_call_loss(
        df, threshold=threshold, target_skill_groups=target_skill_groups
    )

    now = now or datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    checked_at = now.strftime("%Y-%m-%d %H:%M")
    text = cte.build_notification_text(result, checked_at=checked_at)

    payload = {
        "source_csv": csv_path.name,
        "encoding": encoding,
        "checked_at": checked_at,
        "threshold": result.get("threshold"),
        "result": result,
    }
    txt_path, json_path = write_outputs(outbox, stamp, text, payload)

    log_record = None
    if write_log:
        log_record = store.append_log(
            {
                "source": "cli",
                "filename": csv_path.name,
                "encoding": encoding,
                "total_rows": result["total_rows"],
                "outbound_excluded": result["outbound_excluded"],
                "abandon_count": result["abandon_count"],
                "threshold": result["threshold"],
                "alert_count": len(result["alerts"]),
                "txt_output": txt_path.name,
                "json_output": json_path.name,
            }
        )

    return {
        "text": text,
        "result": result,
        "encoding": encoding,
        "txt_path": txt_path,
        "json_path": json_path,
        "log_record": log_record,
    }


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    args = parse_args(argv)
    inbox = Path(args.inbox)
    outbox = Path(args.outbox)

    try:
        # 入力CSVの決定
        if args.csv:
            csv_path = Path(args.csv)
            if not csv_path.is_file():
                print(f"指定CSVが見つかりません: {csv_path}", file=sys.stderr)
                return 1
        else:
            csv_path = find_latest_csv(inbox)
            if csv_path is None:
                print(f"処理対象のCSVが見つかりません: {inbox}", file=sys.stderr)
                return 1

        store = cte.CtE1Store(base_dir=args.data_dir)
        settings = store.load_settings()
        threshold = resolve_threshold(args.threshold, settings)
        target_skill_groups = resolve_target_skill_groups(args.target_skill_group, settings)

        try:
            outcome = process_csv(
                csv_path,
                store=store,
                threshold=threshold,
                target_skill_groups=target_skill_groups,
                outbox=outbox,
                write_log=not args.no_log,
            )
        except cte.CtE1Error as exc:
            print(f"CSV処理エラー: {exc}", file=sys.stderr)
            return 2

        # 通知文プレビューを標準出力へ。出力ファイルパスは標準エラーへ。
        print(outcome["text"])
        print(f"\n[出力] {outcome['txt_path']}", file=sys.stderr)
        print(f"[出力] {outcome['json_path']}", file=sys.stderr)
        return 0

    except Exception as exc:  # noqa: BLE001 - 想定外は終了コード3にまとめる
        print(f"予期しないエラー: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
