import os
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///multimulti_os.db")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_project_columns()


def ensure_project_columns() -> None:
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("projects")}
    statements = []
    if "color" not in existing:
        statements.append("ALTER TABLE projects ADD COLUMN color VARCHAR(20) DEFAULT '#5B6CFF'")
    if "display_order" not in existing:
        statements.append("ALTER TABLE projects ADD COLUMN display_order INTEGER DEFAULT 0")
    if "is_active" not in existing:
        statements.append("ALTER TABLE projects ADD COLUMN is_active BOOLEAN DEFAULT 1")

    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))


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
