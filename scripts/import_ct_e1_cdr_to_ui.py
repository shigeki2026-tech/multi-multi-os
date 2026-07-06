from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.services import answer_rate_service as ar
from src.services.cdr_import_service import CdrImportError
from src.services.container import service_scope
from src.ui.bootstrap import ensure_app_ready


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CT-e1 CSVを既存の応答率UI用DBへ取り込む"
    )
    parser.add_argument("--csv", required=True, help="取込対象CSV")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="CSV対象日と衝突する既存集計を削除して最新CSVへ置換する",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    csv_path = Path(args.csv).expanduser().resolve()

    if not csv_path.is_file():
        print(f"CSVがありません: {csv_path}", file=sys.stderr)
        return 2

    if csv_path.stat().st_size <= 0:
        print(f"CSVが0バイトです: {csv_path}", file=sys.stderr)
        return 2

    raw = csv_path.read_bytes()
    ensure_app_ready()

    try:
        with service_scope() as container:
            service = container.cdr_import_service
            prepared = service.prepare(
                raw,
                csv_path.name,
                dict(ar.DEFAULT_COLUMN_MAPPING),
            )

            stats = prepared.get("stats") or []
            if not stats:
                raise CdrImportError("保存対象の応答率集計が0件です。")

            stat_dates = sorted({row["stat_date"] for row in stats})
            start_date = stat_dates[0]
            end_date = stat_dates[-1]
            replace_result = None

            if prepared.get("collisions"):
                if not args.replace_existing:
                    raise CdrImportError(
                        "同一日・同一時間帯・同一スキルグループの既存データがあります。"
                        "--replace-existing を指定してください。"
                    )

                replace_result = service.delete_call_stats_range(
                    start_date,
                    end_date,
                    actor_id=None,
                    note=(
                        "CT-e1自動取得の最新CSVへ置換: "
                        f"{csv_path.name} / {start_date}〜{end_date}"
                    ),
                )

                prepared = service.prepare(
                    raw,
                    csv_path.name,
                    dict(ar.DEFAULT_COLUMN_MAPPING),
                )

                if prepared.get("collisions"):
                    raise CdrImportError(
                        "既存期間を削除した後も衝突が残っています。"
                    )

            saved = service.commit(
                prepared,
                actor_id=None,
                raw=raw,
            )

            dashboard = container.dashboard_service.get_answer_rate_dashboard_summary()

        result = {
            "status": "completed",
            "csv": str(csv_path),
            "csv_bytes": csv_path.stat().st_size,
            "date_start": str(start_date),
            "date_end": str(end_date),
            "row_count": prepared["row_count"],
            "summary": prepared["summary"],
            "replace_result": replace_result,
            "saved": saved,
            "dashboard": dashboard,
        }

        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        print("RESULT: CT_E1_CDR_UI_IMPORT_SUCCESS")
        return 0

    except CdrImportError as exc:
        print(f"CDR UI取込失敗: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"CDR UI取込予期せぬ失敗: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())