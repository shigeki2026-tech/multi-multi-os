"""Tests for CT-e1 call-loss CSV check (放棄呼のみ集計 / 発信呼除外 / しきい値判定).

Pure functions only — no Streamlit, no DB. Verifies the call-loss aggregation
definition: 呼損量 = 放棄呼=1 only, with 発信呼=1 excluded first, and skill-group
threshold alerts. Also covers required-column validation and cp932 reading.
"""
import io

import pandas as pd
import pytest

from src.services import ct_e1_service as cte


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_only_abandon_one_counted():
    df = _df(
        [
            {"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:01"},
            {"放棄呼": "0", "スキルグループ": "A", "着信時間": "2026-06-01 18:02"},
            {"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:03"},
        ]
    )
    res = cte.aggregate_call_loss(df, threshold=0)
    assert res["abandon_count"] == 2
    assert res["total_rows"] == 3


def test_outbound_one_excluded():
    df = _df(
        [
            {"放棄呼": "1", "発信呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:01"},
            {"放棄呼": "1", "発信呼": "0", "スキルグループ": "A", "着信時間": "2026-06-01 18:02"},
        ]
    )
    res = cte.aggregate_call_loss(df, threshold=0)
    assert res["has_outbound_column"] is True
    assert res["outbound_excluded"] == 1
    # 発信呼=1 の放棄呼は呼損量に含めない
    assert res["abandon_count"] == 1


def test_abandon_zero_excluded():
    df = _df(
        [
            {"放棄呼": "0", "スキルグループ": "A", "着信時間": "2026-06-01 18:01"},
            {"放棄呼": "0", "スキルグループ": "B", "着信時間": "2026-06-01 18:02"},
        ]
    )
    res = cte.aggregate_call_loss(df, threshold=0)
    assert res["abandon_count"] == 0
    assert res["by_skill_group"] == []


def test_missing_required_column_raises():
    df = _df([{"放棄呼": "1", "着信時間": "2026-06-01 18:01"}])  # スキルグループ 欠落
    missing = cte.validate_columns(df.columns)
    assert "スキルグループ" in missing
    with pytest.raises(cte.CtE1Error):
        cte.aggregate_call_loss(df)


def test_reads_cp932_csv():
    df = _df(
        [
            {"放棄呼": "1", "スキルグループ": "横浜", "着信時間": "2026-06-01 18:01"},
        ]
    )
    raw = df.to_csv(index=False).encode("cp932")
    encoding, loaded = cte.detect_and_read(raw)
    # utf-8/utf-8-sig では日本語のcp932バイトを誤読しないことを確認（cp932で読める）
    assert encoding in ("utf-8-sig", "utf-8", "cp932")
    assert "スキルグループ" in loaded.columns
    res = cte.aggregate_call_loss(loaded)
    assert res["abandon_count"] == 1
    assert res["by_skill_group"][0]["skill_group"] == "横浜"


def test_aggregated_by_skill_group():
    df = _df(
        [
            {"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:01"},
            {"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:02"},
            {"放棄呼": "1", "スキルグループ": "B", "着信時間": "2026-06-01 18:03"},
            {"放棄呼": "0", "スキルグループ": "B", "着信時間": "2026-06-01 18:04"},
        ]
    )
    res = cte.aggregate_call_loss(df, threshold=0)
    by = {r["skill_group"]: r["abandon_count"] for r in res["by_skill_group"]}
    assert by == {"A": 2, "B": 1}
    # 放棄呼数の多い順
    assert res["by_skill_group"][0]["skill_group"] == "A"


def test_threshold_alerts_only_at_or_above():
    df = _df(
        [
            {"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:01"},
            {"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:02"},
            {"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:03"},
            {"放棄呼": "1", "スキルグループ": "B", "着信時間": "2026-06-01 18:04"},
        ]
    )
    res = cte.aggregate_call_loss(df, threshold=3)
    alert_groups = {a["skill_group"] for a in res["alerts"]}
    assert alert_groups == {"A"}  # A=3 (>=3), B=1 (<3)


def test_threshold_no_alert_when_below():
    df = _df(
        [
            {"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:01"},
            {"放棄呼": "1", "スキルグループ": "B", "着信時間": "2026-06-01 18:02"},
        ]
    )
    res = cte.aggregate_call_loss(df, threshold=10)
    assert res["alerts"] == []
    text = cte.build_notification_text(res)
    assert "しきい値超過なし" in text


def test_target_skill_groups_filter():
    df = _df(
        [
            {"放棄呼": "1", "スキルグループ": "A", "着信時間": "2026-06-01 18:01"},
            {"放棄呼": "1", "スキルグループ": "B", "着信時間": "2026-06-01 18:02"},
        ]
    )
    res = cte.aggregate_call_loss(df, threshold=0, target_skill_groups=["A"])
    assert res["abandon_count"] == 1
    assert {r["skill_group"] for r in res["by_skill_group"]} == {"A"}
