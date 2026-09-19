"""Pytest configuration and shared fixtures for WeAutomate."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from weautomate.database.models import Base
from weautomate.database.session import seed_default_entitlements, get_db
from weautomate.controller.app import app
from weautomate.hypervisor.mock import MockHypervisorAdapter
from weautomate.controller.routes.reconciliation import get_hypervisor_adapter


@pytest.fixture(scope="function")
def db_engine():
    """In-memory SQLite engine with StaticPool for cross-thread consistency."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provides an isolated database session with default 80-core entitlement."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    seed_default_entitlements(session, core_quantity=80)
    yield session
    session.close()


@pytest.fixture(scope="function")
def mock_hypervisor():
    """Provides a fresh mock hypervisor adapter."""
    return MockHypervisorAdapter()


@pytest.fixture(scope="function")
def client(db_session, mock_hypervisor):
    """FastAPI TestClient with overridden database and hypervisor dependencies."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_hypervisor():
        return mock_hypervisor

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_hypervisor_adapter] = override_get_hypervisor

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
