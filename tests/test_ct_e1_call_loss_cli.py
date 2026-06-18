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
