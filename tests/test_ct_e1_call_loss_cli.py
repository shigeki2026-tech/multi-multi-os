"""Tests for the CT-e1 call-loss CLI wrapper (scripts/run_ct_e1_call_loss_check.py).

Exercises the CLI through main(argv) only — no Streamlit, no DB, no network.
Verifies inbox selection, output file creation, exit codes, --csv override and
--no-log behavior. The module is loaded by file path because a `scripts`
namespace from site-packages would otherwise shadow the local one.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_SCRIPT_PATH = REPO_ROOT / "scripts" / "run_ct_e1_call_loss_check.py"
_spec = importlib.util.spec_from_file_location("run_ct_e1_call_loss_check", _SCRIPT_PATH)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _write_csv(path: Path, rows: list[dict], mtime: float | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pd.DataFrame(rows).to_csv(index=False).encode("utf-8"))
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def _dirs(tmp_path: Path) -> dict:
    return {
        "inbox": tmp_path / "inbox",
        "outbox": tmp_path / "outbox",
        "data": tmp_path / "data",
    }


def _argv(d: dict, *extra: str) -> list[str]:
    return [
        "--inbox", str(d["inbox"]),
        "--outbox", str(d["outbox"]),
        "--data-dir", str(d["data"]),
        *extra,
    ]


def _outputs(outbox: Path):
    return sorted(outbox.glob("ct_e1_call_loss_*.txt")), sorted(outbox.glob("ct_e1_call_loss_*.json"))


_ONE_ABANDON = [{"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:01"}]


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------
def test_no_csv_in_inbox_returns_1(tmp_path):
    d = _dirs(tmp_path)
    d["inbox"].mkdir(parents=True)  # exists but empty
    assert cli.main(_argv(d)) == 1
    txt, js = _outputs(d["outbox"])
    assert txt == [] and js == []


def test_valid_csv_creates_outputs_and_returns_0(tmp_path):
    d = _dirs(tmp_path)
    _write_csv(d["inbox"] / "report.csv", _ONE_ABANDON)
    assert cli.main(_argv(d)) == 0
    txt, js = _outputs(d["outbox"])
    assert len(txt) == 1 and len(js) == 1
    assert "CT-e1 呼損確認" in txt[0].read_text(encoding="utf-8")


def test_missing_required_columns_returns_2(tmp_path):
    d = _dirs(tmp_path)
    # スキルグループ 欠落 → 必須列エラー
    _write_csv(d["inbox"] / "bad.csv", [{"放棄呼": "1", "着信時間": "2026-06-01 18:01"}])
    assert cli.main(_argv(d)) == 2
    txt, js = _outputs(d["outbox"])
    assert txt == [] and js == []


def test_newest_csv_is_selected(tmp_path):
    d = _dirs(tmp_path)
    _write_csv(
        d["inbox"] / "old.csv",
        [{"放棄呼": "1", "スキルグループ": "OLD", "着信時間": "2026-06-01 18:01"}],
        mtime=1_000_000,
    )
    _write_csv(
        d["inbox"] / "new.csv",
        [{"放棄呼": "1", "スキルグループ": "NEW", "着信時間": "2026-06-02 18:01"}],
        mtime=2_000_000,
    )
    assert cli.main(_argv(d)) == 0
    _, js = _outputs(d["outbox"])
    payload = __import__("json").loads(js[0].read_text(encoding="utf-8"))
    assert payload["source_csv"] == "new.csv"
    groups = {r["skill_group"] for r in payload["result"]["by_skill_group"]}
    assert groups == {"NEW"}


def test_explicit_csv_overrides_inbox(tmp_path):
    d = _dirs(tmp_path)
    # inbox には新しい "wrong" を置くが、--csv で別ファイルを明示する
    _write_csv(
        d["inbox"] / "wrong.csv",
        [{"放棄呼": "1", "スキルグループ": "WRONG", "着信時間": "2026-06-03 18:01"}],
        mtime=9_000_000,
    )
    explicit = _write_csv(
        tmp_path / "explicit.csv",
        [{"放棄呼": "1", "スキルグループ": "RIGHT", "着信時間": "2026-06-01 18:01"}],
    )
    assert cli.main(_argv(d, "--csv", str(explicit))) == 0
    _, js = _outputs(d["outbox"])
    payload = __import__("json").loads(js[0].read_text(encoding="utf-8"))
    assert payload["source_csv"] == "explicit.csv"
    groups = {r["skill_group"] for r in payload["result"]["by_skill_group"]}
    assert groups == {"RIGHT"}


def test_no_log_skips_append(tmp_path):
    d = _dirs(tmp_path)
    _write_csv(d["inbox"] / "report.csv", _ONE_ABANDON)
    log_path = d["data"] / "run_log.jsonl"

    # --no-log: 実行ログは作られない
    assert cli.main(_argv(d, "--no-log")) == 0
    assert not log_path.exists()

    # 通常実行: 実行ログが追記される
    assert cli.main(_argv(d)) == 0
    assert log_path.exists()
    assert log_path.read_text(encoding="utf-8").strip() != ""


# ---------------------------------------------------------------------------
# 共有フォルダ運用: --move-processed / --processed-dir
# ---------------------------------------------------------------------------
def _log_records(data_dir: Path) -> list:
    import json

    log_path = data_dir / "run_log.jsonl"
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_move_processed_moves_csv_to_processed_dir(tmp_path):
    d = _dirs(tmp_path)
    processed = tmp_path / "processed"
    src = _write_csv(d["inbox"] / "report.csv", _ONE_ABANDON)

    rc = cli.main(_argv(d, "--processed-dir", str(processed), "--move-processed"))
    assert rc == 0
    # 元CSVはinboxから消え、processedへ同名で移動している
    assert not src.exists()
    assert (processed / "report.csv").exists()
    # 出力(.txt/.json)は通常どおり作られる
    txt, js = _outputs(d["outbox"])
    assert len(txt) == 1 and len(js) == 1


def test_move_processed_requires_processed_dir(tmp_path):
    d = _dirs(tmp_path)
    _write_csv(d["inbox"] / "report.csv", _ONE_ABANDON)
    # --processed-dir なしの --move-processed は引数不整合エラー(2)
    assert cli.main(_argv(d, "--move-processed")) == 2


def test_source_csv_stays_in_inbox_on_validation_error(tmp_path):
    d = _dirs(tmp_path)
    processed = tmp_path / "processed"
    # スキルグループ欠落 → 必須列エラー(2)。--move-processed を付けても移動しない。
    src = _write_csv(
        d["inbox"] / "bad.csv", [{"放棄呼": "1", "着信時間": "2026-06-01 18:01"}]
    )
    rc = cli.main(_argv(d, "--processed-dir", str(processed), "--move-processed"))
    assert rc == 2
    assert src.exists()  # 元CSVはinboxに残る
    assert not processed.exists() or list(processed.glob("*.csv")) == []


def test_move_processed_collision_adds_timestamp_suffix(tmp_path):
    d = _dirs(tmp_path)
    processed = tmp_path / "processed"
    # processed に既に同名ファイルがある状態を作る
    processed.mkdir(parents=True)
    (processed / "report.csv").write_text("already here", encoding="utf-8")

    src = _write_csv(d["inbox"] / "report.csv", _ONE_ABANDON)
    rc = cli.main(_argv(d, "--processed-dir", str(processed), "--move-processed"))
    assert rc == 0
    assert not src.exists()
    # 既存 report.csv は温存され、別名で退避されている
    assert (processed / "report.csv").read_text(encoding="utf-8") == "already here"
    moved = [p for p in processed.glob("report_*.csv")]
    assert len(moved) == 1
    assert moved[0].name != "report.csv"


def test_run_log_preserves_japanese_filename(tmp_path):
    d = _dirs(tmp_path)
    name = "通話呼詳細V3.5(CSV)_20260622141933.csv"
    _write_csv(d["inbox"] / name, _ONE_ABANDON)

    assert cli.main(_argv(d)) == 0
    records = _log_records(d["data"])
    assert len(records) == 1
    # run_log.jsonl はUTF-8で書かれ、実際のWindowsファイル名を文字化けなく保持する
    assert records[0]["filename"] == name


def test_move_processed_helper_unc_style_paths(tmp_path):
    # UNC運用を模した tmp_path テスト（実ネットワーク不要）。
    # 退避先フォルダが未作成でも作成され、元名を保持して移動できる。
    inbox = tmp_path / "share" / "inbox"
    processed = tmp_path / "share" / "processed"
    src = _write_csv(inbox / "通話呼詳細.csv", _ONE_ABANDON)

    dest = cli.move_processed_csv(src, processed)
    assert dest == processed / "通話呼詳細.csv"
    assert dest.exists()
    assert not src.exists()
