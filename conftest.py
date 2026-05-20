"""
Pytest configuration for Crystal Supplier Email Service tests
"""

import os
import asyncio
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment - use SQLite for testing"""
    os.environ["USE_SQLITE"] = "true"
    os.environ["TESTING"] = "true"
    print("\n✅ Test environment configured: Using SQLite database")
    yield


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Initialize test database with schema"""
    from backend.database import Base, engine, USE_SQLITE
    
    if not USE_SQLITE:
        print("⚠️  Not using SQLite - skipping database initialization")
        return
    
    # Create all tables using asyncio
    async def create_tables():
        print("\n📋 Creating test database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Test database initialized")
    
    asyncio.run(create_tables())
    yield
