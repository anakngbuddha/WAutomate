"""Database engine and session management for WeAutomate."""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from weautomate.config import settings
from weautomate.database.models import Base, Entitlement, LicenseType


def get_engine(db_url: str = None):
    url = db_url or settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, echo=False)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine=None):
    """Create all database tables."""
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


def seed_default_entitlements(db_session: Session, core_quantity: int = 80):
    """Seed initial FVB entitlement pool if none exists."""
    existing = db_session.execute(select(Entitlement)).scalars().first()
    if not existing:
        default_entitlement = Entitlement(
            product=settings.default_product,
            edition=settings.default_edition,
            version=settings.default_version,
            license_type=LicenseType.SUBSCRIPTION,
            core_quantity=core_quantity,
            agreement_ref="MS-EA-FVB-2025-001",
        )
        db_session.add(default_entitlement)
        db_session.commit()
        db_session.refresh(default_entitlement)
        return default_entitlement
    return existing


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
