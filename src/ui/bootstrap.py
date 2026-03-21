from datetime import date, timedelta

from sqlalchemy import select

from src.models.entities import AppRegistry, LeocSnapshot, Project, Task, Team, User
from src.repositories.db import get_session, init_db


def ensure_app_ready():
    init_db()
    seed_if_needed()
    ensure_registry_entries()


def seed_if_needed():
    with get_session() as session:
        existing_user = session.scalar(select(User.user_id).limit(1))
        if existing_user is not None:
            return

        team1 = Team(team_name="\u30de\u30eb\u30c1\u4e00\u6b21\u53d7\u3051", display_order=10, is_active=True, description="\u4e00\u6b21\u53d7\u4ed8\u30c1\u30fc\u30e0")
        team2 = Team(team_name="\u30de\u30eb\u30c1\u904b\u7528\u7ba1\u7406", display_order=20, is_active=True, description="\u904b\u7528\u7ba1\u7406\u30c1\u30fc\u30e0")
        session.add_all([team1, team2])
        session.flush()

        users = [
            User(google_email="ohama@example.com", display_name="\u5927\u6ff1 \u7ba1\u7406\u8005", email="ohama@example.com", role="admin", team_id=team1.team_id, is_active=True),
            User(google_email="yamada@example.com", display_name="\u5c71\u7530SV", email="yamada@example.com", role="sv", team_id=team1.team_id, is_active=True),
            User(google_email="sato@example.com", display_name="\u4f50\u85e4SV", email="sato@example.com", role="sv", team_id=team1.team_id, is_active=True),
            User(google_email="tanaka@example.com", display_name="\u7530\u4e2dSV", email="tanaka@example.com", role="sv", team_id=team2.team_id, is_active=True),
        ]
        session.add_all(users)
        session.flush()

        projects = [
            Project(project_name="\u53d7\u96fbA", team_id=team1.team_id, color="#4F8CFF", display_order=10, is_active=True),
            Project(project_name="\u5165\u96fb\u76e3\u8996", team_id=team1.team_id, color="#34C759", display_order=20, is_active=True),
            Project(project_name="\u54c1\u8cea\u7ba1\u7406", team_id=team2.team_id, color="#FF9F0A", display_order=30, is_active=True),
        ]
        session.add_all(projects)
        session.flush()

        session.add_all(
            [
                Task(
                    task_type="personal_task",
                    title="\u671d\u4f1a\u306e\u9032\u884c\u30c1\u30a7\u30c3\u30af",
                    description="\u672c\u65e5\u306e\u671d\u4f1a\u9032\u884c\u3092\u78ba\u8a8d",
                    requester_user_id=users[0].user_id,
                    assignee_user_id=users[1].user_id,
                    team_id=team1.team_id,
                    project_id=projects[0].project_id,
                    priority="\u9ad8",
                    status="\u9032\u884c\u4e2d",
                    due_date=date.today(),
                    needs_confirmation=False,
                    is_active=True,
                ),
                Task(
                    task_type="team_task",
                    title="\u5831\u544a\u6570\u5024\u306e\u78ba\u8a8d",
                    description="\u65e5\u6b21\u306e\u96c6\u8a08\u6570\u5024\u3092\u78ba\u8a8d",
                    requester_user_id=users[1].user_id,
                    assignee_user_id=users[2].user_id,
                    team_id=team1.team_id,
                    project_id=projects[1].project_id,
                    priority="\u4e2d",
                    status="\u672a\u5bfe\u5fdc",
                    due_date=date.today(),
                    needs_confirmation=False,
                    is_active=True,
                ),
                Task(
                    task_type="handover_task",
                    title="\u524d\u65e5\u672a\u5bfe\u5fdc\u306e\u78ba\u8a8d",
                    description="\u672a\u5bfe\u5fdc\u6848\u4ef6\u3092\u78ba\u8a8d",
                    requester_user_id=users[2].user_id,
                    assignee_user_id=users[1].user_id,
                    team_id=team1.team_id,
                    project_id=projects[2].project_id,
                    priority="\u9ad8",
                    status="\u78ba\u8a8d\u5f85\u3061",
                    due_date=date.today() - timedelta(days=1),
                    needs_confirmation=True,
                    is_active=True,
                ),
                Task(
                    task_type="sv_request",
                    title="14\u6642\u901f\u5831\u306e\u4f5c\u6210",
                    description="14:00\u6642\u70b9\u306e\u901f\u5831\u3092\u4f5c\u6210\u3057\u3066\u304f\u3060\u3055\u3044",
                    requester_user_id=users[2].user_id,
                    assignee_user_id=users[1].user_id,
                    team_id=team1.team_id,
                    project_id=projects[0].project_id,
                    priority="\u9ad8",
                    status="\u78ba\u8a8d\u5f85\u3061",
                    requested_date=date.today(),
                    due_date=date.today(),
                    needs_confirmation=True,
                    related_link="https://example.local/summary",
                    is_active=True,
                ),
                LeocSnapshot(
                    snapshot_time="13:00",
                    inbound_count=6,
                    lost_count=2,
                    answer_rate=75.0,
                    ai_count=4,
                    form_count=6,
                    source_type="seed",
                    source_ref="sample",
                    created_by=users[1].user_id,
                ),
            ]
        )

        session.add_all(
            [
                AppRegistry(app_key="tasks", app_name="\u30bf\u30b9\u30af", description="\u30bf\u30b9\u30af\u7ba1\u7406", display_order=1),
                AppRegistry(app_key="requests", app_name="SV\u4f9d\u983c", description="SV\u4f9d\u983c\u7ba1\u7406", display_order=2),
                AppRegistry(app_key="leoc", app_name="\u5fdc\u7b54\u7387\u901f\u5831", description="\u5fdc\u7b54\u7387\u901f\u5831", display_order=3),
                AppRegistry(app_key="reports", app_name="\u65e5\u5831\u9001\u4fe1", description="\u65e5\u5831\u9001\u4fe1", display_order=4),
                AppRegistry(app_key="call_details", app_name="\u547c\u8a73\u7d30\u4f5c\u6210", description="\u547c\u8a73\u7d30\u4f5c\u6210", display_order=5),
                AppRegistry(app_key="attendance", app_name="\u6253\u523b\u7167\u5408", description="\u6708\u6b21\u7de0\u3081\u5411\u3051\u306e\u6253\u523b\u7167\u5408", display_order=6),
            ]
        )


def ensure_registry_entries():
    desired_apps = [
        {"app_key": "tasks", "app_name": "\u30bf\u30b9\u30af", "description": "\u30bf\u30b9\u30af\u7ba1\u7406", "display_order": 1},
        {"app_key": "requests", "app_name": "SV\u4f9d\u983c", "description": "SV\u4f9d\u983c\u7ba1\u7406", "display_order": 2},
        {"app_key": "leoc", "app_name": "\u5fdc\u7b54\u7387\u901f\u5831", "description": "\u5fdc\u7b54\u7387\u901f\u5831", "display_order": 3},
        {"app_key": "reports", "app_name": "\u65e5\u5831\u9001\u4fe1", "description": "\u65e5\u5831\u9001\u4fe1", "display_order": 4},
        {"app_key": "call_details", "app_name": "\u547c\u8a73\u7d30\u4f5c\u6210", "description": "\u547c\u8a73\u7d30\u4f5c\u6210", "display_order": 5},
        {"app_key": "attendance", "app_name": "\u6253\u523b\u7167\u5408", "description": "\u6708\u6b21\u7de0\u3081\u5411\u3051\u306e\u6253\u523b\u7167\u5408", "display_order": 6},
    ]
    with get_session() as session:
        existing = {app.app_key: app for app in session.scalars(select(AppRegistry)).all()}
        changed = False
        for item in desired_apps:
            app = existing.get(item["app_key"])
            if app is None:
                session.add(AppRegistry(is_enabled=True, **item))
                changed = True
                continue
            if (
                app.app_name != item["app_name"]
                or app.description != item["description"]
                or app.display_order != item["display_order"]
                or not app.is_enabled
            ):
                app.app_name = item["app_name"]
                app.description = item["description"]
                app.display_order = item["display_order"]
                app.is_enabled = True
                changed = True
        if changed:
            session.flush()
