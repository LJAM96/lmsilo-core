"""
Shared pytest fixtures for LMSilo tests.

Provides common fixtures for database sessions, test clients, and mocks.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_celery_app():
    """Create a mock Celery app for testing tasks."""
    app = MagicMock()
    app.task = MagicMock(side_effect=lambda *args, **kwargs: lambda f: f)
    return app


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.publish = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def mock_model_manager():
    """Create a mock model manager for ML models."""
    manager = MagicMock()
    manager.load_model = MagicMock(return_value=MagicMock())
    manager.get_predictor = MagicMock(return_value=MagicMock())
    manager.is_loaded = MagicMock(return_value=True)
    return manager


# Common test data
@pytest.fixture
def sample_job_data():
    """Sample job creation data."""
    return {
        "status": "pending",
        "priority": 5,
        "options": {"top_k": 5},
    }


@pytest.fixture
def sample_audit_data():
    """Sample audit log data."""
    return {
        "service": "test",
        "action": "test_action",
        "username": "test_user",
        "ip_address": "127.0.0.1",
        "status": "success",
    }
