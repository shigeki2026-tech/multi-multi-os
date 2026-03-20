from datetime import date, timedelta

from sqlalchemy import select

from src.models.entities import AppRegistry, LeocSnapshot, Project, Task, Team, User
from src.repositories.db import get_session, init_db


def ensure_app_ready():
    init_db()
    seed_if_needed()


def seed_if_needed():
    with get_session() as session:
        existing_user = session.scalar(select(User.user_id).limit(1))
        if existing_user is not None:
            return

        team1 = Team(team_name="マルチ業務1課", display_order=10, is_active=True, description="一次対応チーム")
        team2 = Team(team_name="マルチ業務2課", display_order=20, is_active=True, description="品質確認チーム")
        session.add_all([team1, team2])
        session.flush()

        users = [
            User(google_email="ohama@example.com", display_name="大濱成基", email="ohama@example.com", role="admin", team_id=team1.team_id, is_active=True),
            User(google_email="yamada@example.com", display_name="山田SV", email="yamada@example.com", role="sv", team_id=team1.team_id, is_active=True),
            User(google_email="sato@example.com", display_name="佐藤SV", email="sato@example.com", role="sv", team_id=team1.team_id, is_active=True),
            User(google_email="tanaka@example.com", display_name="田中SV", email="tanaka@example.com", role="sv", team_id=team2.team_id, is_active=True),
        ]
        session.add_all(users)
        session.flush()

        projects = [
            Project(project_name="案件A", team_id=team1.team_id, color="#4F8CFF", display_order=10, is_active=True),
            Project(project_name="入電管理", team_id=team1.team_id, color="#34C759", display_order=20, is_active=True),
            Project(project_name="品質確認", team_id=team2.team_id, color="#FF9F0A", display_order=30, is_active=True),
        ]
        session.add_all(projects)
        session.flush()

        session.add_all(
            [
                Task(
                    task_type="personal_task",
                    title="午前中の件数チェック",
                    description="本日の件数を確認",
                    requester_user_id=users[0].user_id,
                    assignee_user_id=users[1].user_id,
                    team_id=team1.team_id,
                    project_id=projects[0].project_id,
                    priority="高",
                    status="進行中",
                    due_date=date.today(),
                    needs_confirmation=False,
                    is_active=True,
                ),
                Task(
                    task_type="team_task",
                    title="引継ぎ内容の整理",
                    description="前日からの引継ぎ事項を整理",
                    requester_user_id=users[1].user_id,
                    assignee_user_id=users[2].user_id,
                    team_id=team1.team_id,
                    project_id=projects[1].project_id,
                    priority="中",
                    status="未着手",
                    due_date=date.today(),
                    needs_confirmation=False,
                    is_active=True,
                ),
                Task(
                    task_type="handover_task",
                    title="昨日未対応の確認",
                    description="未対応案件の有無を確認",
                    requester_user_id=users[2].user_id,
                    assignee_user_id=users[1].user_id,
                    team_id=team1.team_id,
                    project_id=projects[2].project_id,
                    priority="高",
                    status="確認待ち",
                    due_date=date.today() - timedelta(days=1),
                    needs_confirmation=True,
                    is_active=True,
                ),
                Task(
                    task_type="sv_request",
                    title="14時速報の作成",
                    description="14:00時点の速報を作成してください",
                    requester_user_id=users[2].user_id,
                    assignee_user_id=users[1].user_id,
                    team_id=team1.team_id,
                    project_id=projects[0].project_id,
                    priority="高",
                    status="確認待ち",
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
                AppRegistry(app_key="tasks", app_name="タスク", description="タスク管理", display_order=1),
                AppRegistry(app_key="requests", app_name="SV依頼", description="SV依頼管理", display_order=2),
                AppRegistry(app_key="leoc", app_name="応答率速報", description="応答率速報", display_order=3),
                AppRegistry(app_key="reports", app_name="日報送信", description="日報送信", display_order=4),
                AppRegistry(app_key="call_details", app_name="呼詳細作成", description="呼詳細作成", display_order=5),
            ]
        )
