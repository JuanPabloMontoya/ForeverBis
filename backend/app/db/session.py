"""SQLAlchemy engine and session factory lifecycle."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 2},
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def check_database_connection(engine: Engine) -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def get_session(request: Request) -> Generator[Session, None, None]:
    """FastAPI dependency wired to the active app session factory."""
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session
