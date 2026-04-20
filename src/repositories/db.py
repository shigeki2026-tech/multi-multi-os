import os
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base


def _get_database_url() -> str:
    try:
        import streamlit as st
        url = st.secrets.get("DATABASE_URL")
        if url:
            return str(url)
    except Exception:
        pass
    return os.getenv("DATABASE_URL", "sqlite:///multimulti_os.db")


DATABASE_URL = _get_database_url()
engine = create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_user_columns()
    ensure_team_columns()
    ensure_project_columns()
    ensure_task_columns()


def ensure_user_columns() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    statements = []
    if "google_email" not in existing:
        statements.append("ALTER TABLE users ADD COLUMN google_email VARCHAR(255)")
    if "last_login_at" not in existing:
        statements.append("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP")
    if statements:
        with engine.begin() as conn:
            for s in statements:
                conn.execute(text(s))
            conn.execute(text("UPDATE users SET google_email = email WHERE google_email IS NULL AND email IS NOT NULL"))


def ensure_team_columns() -> None:
    inspector = inspect(engine)
    if "teams" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("teams")}
    statements = []
    if "display_order" not in existing:
        statements.append("ALTER TABLE teams ADD COLUMN display_order INTEGER DEFAULT 0")
    if "is_active" not in existing:
        statements.append("ALTER TABLE teams ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
    if "description" not in existing:
        statements.append("ALTER TABLE teams ADD COLUMN description TEXT")
    if statements:
        with engine.begin() as conn:
            for s in statements:
                conn.execute(text(s))


def ensure_project_columns() -> None:
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("projects")}
    statements = []
    if "color" not in existing:
        statements.append("ALTER TABLE projects ADD COLUMN color VARCHAR(20) DEFAULT '#4F8CFF'")
    if "display_order" not in existing:
        statements.append("ALTER TABLE projects ADD COLUMN display_order INTEGER DEFAULT 0")
    if "is_active" not in existing:
        statements.append("ALTER TABLE projects ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
    if statements:
        with engine.begin() as conn:
            for s in statements:
                conn.execute(text(s))


def ensure_task_columns() -> None:
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("tasks")}
    statements = []
    if "is_active" not in existing:
        statements.append("ALTER TABLE tasks ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
    if "deleted_by" not in existing:
        statements.append("ALTER TABLE tasks ADD COLUMN deleted_by INTEGER")
    if statements:
        with engine.begin() as conn:
            for s in statements:
                conn.execute(text(s))


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
