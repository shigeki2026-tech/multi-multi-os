"""Tests for business-group editing (add/remove child lines on skill_group_merge).

In-memory SQLite. Does not touch the answer-rate calculation logic or existing
storage formats; only verifies add / reactivate / duplicate-skip / remove
(logical deletion) / search behavior. Labels and lines use ASCII to avoid any
encoding ambiguity; the test semantics are unchanged.
"""
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

import src.models.entities  # noqa: F401  register all tables onto the metadata
from src.models.base import Base
from src.models.entities import SkillGroupMerge
from src.repositories.answer_rate_master_repository import AnswerRateMasterRepository
from src.services.answer_rate_master_service import AnswerRateMasterService


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess = sessionmaker(bind=engine)()
    try:
        yield sess
    finally:
        sess.close()


@pytest.fixture()
def svc(session):
    return AnswerRateMasterService(AnswerRateMasterRepository(session), audit_service=None)


def _count(session, **where) -> int:
    stmt = select(func.count(SkillGroupMerge.id))
    for k, v in where.items():
        stmt = stmt.where(getattr(SkillGroupMerge, k) == v)
    return int(session.scalar(stmt) or 0)


def test_add_new_pair_inserts_active(svc, session):
    res = svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["line_a"])
    assert res == {"added": 1, "reactivated": 0, "skipped": 0, "label": "group_lawyer"}
    row = session.scalar(
        select(SkillGroupMerge).where(
            SkillGroupMerge.merge_label == "group_lawyer",
            SkillGroupMerge.child_skill_group == "line_a",
        )
    )
    assert row is not None and row.is_active is True


def test_add_existing_inactive_pair_reactivates(svc, session):
    svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["line_a"])
    svc.deactivate_child_skill_groups_from_merge(1, "group_lawyer", ["line_a"])
    assert _count(session, merge_label="group_lawyer", child_skill_group="line_a", is_active=False) == 1

    res = svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["line_a"])
    assert res["reactivated"] == 1 and res["added"] == 0 and res["skipped"] == 0
    # No new physical row (still a single row), and it is back to active.
    assert _count(session, merge_label="group_lawyer", child_skill_group="line_a") == 1
    assert _count(session, merge_label="group_lawyer", child_skill_group="line_a", is_active=True) == 1


def test_add_existing_active_pair_is_skipped(svc):
    svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["line_a"])
    res = svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["line_a"])
    assert res == {"added": 0, "reactivated": 0, "skipped": 1, "label": "group_lawyer"}


def test_deactivate_sets_inactive_without_physical_delete(svc, session):
    svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["line_a", "line_b"])
    before = _count(session)
    n = svc.deactivate_child_skill_groups_from_merge(1, "group_lawyer", ["line_a"])
    assert n == 1
    # Row count is unchanged (no physical delete).
    assert _count(session) == before
    assert _count(session, child_skill_group="line_a", is_active=False) == 1
    assert _count(session, child_skill_group="line_b", is_active=True) == 1


def test_deactivate_already_inactive_returns_zero(svc):
    svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["line_a"])
    svc.deactivate_child_skill_groups_from_merge(1, "group_lawyer", ["line_a"])
    assert svc.deactivate_child_skill_groups_from_merge(1, "group_lawyer", ["line_a"]) == 0


def test_search_filters_by_keyword(svc):
    skill_groups = ["dotcom_yokohama_01", "dotcom_tokyo_01", "yoshikei_shiga_a"]
    res = svc.search_child_skill_groups(skill_groups, "yokohama", "group_lawyer")
    names = [r["child_skill_group"] for r in res]
    assert names == ["dotcom_yokohama_01"]


def test_search_only_unregistered_excludes_active_members(svc):
    skill_groups = ["dotcom_yokohama_01", "dotcom_yokohama_02"]
    svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["dotcom_yokohama_01"])
    # only_unregistered=True (default) -> active members are excluded from candidates.
    res = svc.search_child_skill_groups(skill_groups, "yokohama", "group_lawyer", only_unregistered=True)
    names = [r["child_skill_group"] for r in res]
    assert names == ["dotcom_yokohama_02"]
    # only_unregistered=False -> registered members also appear.
    res2 = svc.search_child_skill_groups(skill_groups, "yokohama", "group_lawyer", only_unregistered=False)
    assert sorted(r["child_skill_group"] for r in res2) == [
        "dotcom_yokohama_01",
        "dotcom_yokohama_02",
    ]


def test_search_inactive_member_flagged_for_reactivation(svc):
    skill_groups = ["dotcom_yokohama_01"]
    svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["dotcom_yokohama_01"])
    svc.deactivate_child_skill_groups_from_merge(1, "group_lawyer", ["dotcom_yokohama_01"])
    res = svc.search_child_skill_groups(skill_groups, "yokohama", "group_lawyer", only_unregistered=True)
    assert len(res) == 1 and res[0]["already_inactive"] is True


def test_search_limit_caps_results(svc):
    skill_groups = [f"dotcom_yokohama_{i:03d}" for i in range(150)]
    res = svc.search_child_skill_groups(skill_groups, "yokohama", "group_lawyer", limit=100)
    assert len(res) == 100


def test_list_merge_labels_filters_and_prioritizes_active(svc):
    svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["line_a"])
    svc.add_child_skill_groups_to_merge(1, "group_yoshikei", ["line_b"])
    # Make a label that has only inactive rows.
    svc.add_child_skill_groups_to_merge(1, "group_lawyer_paused", ["line_c"])
    svc.deactivate_child_skill_groups_from_merge(1, "group_lawyer_paused", ["line_c"])

    labels = svc.list_merge_labels("lawyer")
    assert labels == ["group_lawyer", "group_lawyer_paused"]  # active first, inactive-only last
    assert svc.list_merge_labels("yoshikei") == ["group_yoshikei"]


def test_get_children_respects_include_inactive(svc):
    svc.add_child_skill_groups_to_merge(1, "group_lawyer", ["line_a", "line_b"])
    svc.deactivate_child_skill_groups_from_merge(1, "group_lawyer", ["line_b"])
    active_only = svc.get_skill_group_merge_children("group_lawyer", include_inactive=False)
    assert [r["child_skill_group"] for r in active_only] == ["line_a"]
    with_inactive = svc.get_skill_group_merge_children("group_lawyer", include_inactive=True)
    assert {r["child_skill_group"] for r in with_inactive} == {"line_a", "line_b"}
