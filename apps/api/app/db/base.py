"""Base declarativa, engine e sessão do SQLAlchemy."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session():
    """Dependency FastAPI: cede uma sessão e garante o fechamento."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
