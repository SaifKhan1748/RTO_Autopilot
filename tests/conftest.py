"""
Shared test fixtures and configuration for pytest.
"""
import pytest
import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app.main import app
from app.core.database import Base, get_db
from app.models.models import Staff, Office, Customer, Case, Event, Document, PasswordReset, PendingReminder, ChecklistConfig

# Test database URL (use SQLite for tests)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Custom SQLite setup to handle ARRAY type (PostgreSQL-specific)
# We'll create tables without the PolicyChunk table which uses ARRAY type
def create_test_tables():
    """Create test tables, excluding PolicyChunk which uses PostgreSQL-specific ARRAY type."""
    # Get all tables except PolicyChunk
    tables_to_create = [
        Staff.__table__,
        Office.__table__,
        Customer.__table__,
        Case.__table__,
        Document.__table__,
        Event.__table__,
        PendingReminder.__table__,
        ChecklistConfig.__table__,
        PasswordReset.__table__
    ]
    
    for table in tables_to_create:
        table.create(test_engine, checkfirst=True)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    """
    # Create all tables (excluding PolicyChunk which uses PostgreSQL-specific types)
    create_test_tables()
    
    # Create session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def test_client(db_session):
    """
    Create a test client with a fresh database and clean rate limits.
    """
    # Override the database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Reset in-memory rate limiter so each test starts with fresh limits
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()
    
    with TestClient(app) as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()
    if hasattr(app.state, "limiter"):
        app.state.limiter.reset()


@pytest.fixture
def test_office(db_session):
    """
    Create a test office.
    """
    office = Office(
        name="Test Office",
        code="TEST001",
        display_name="Test Office Display"
    )
    db_session.add(office)
    db_session.commit()
    db_session.refresh(office)
    return office


@pytest.fixture
def test_staff(db_session, test_office):
    """
    Create a test staff member with known credentials.
    """
    password_hash = bcrypt.hashpw("testpassword123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    staff = Staff(
        office_id=test_office.id,
        email="test@example.com",
        password_hash=password_hash,
        full_name="Test Staff",
        role="staff",
        is_active=1
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


@pytest.fixture
def test_admin(db_session, test_office):
    """
    Create a test admin with known credentials.
    """
    password_hash = bcrypt.hashpw("adminpassword123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    admin = Staff(
        office_id=test_office.id,
        email="admin@example.com",
        password_hash=password_hash,
        full_name="Test Admin",
        role="admin",
        is_active=1
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def test_customer(db_session, test_office):
    """
    Create a test customer.
    """
    customer = Customer(
        office_id=test_office.id,
        full_name="John Doe",
        phone="555-1234",
        email="john@example.com",
        address="123 Test St"
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def authenticated_client(test_client, test_staff):
    """
    Create a test client with an authenticated session.
    """
    # Login to create session
    response = test_client.post("/login", data={
        "email": test_staff.email,
        "password": "testpassword123"
    }, follow_redirects=False)
    
    # The test client should maintain session cookies
    return test_client


@pytest.fixture
def authenticated_admin_client(test_client, test_admin):
    """
    Create a test client with an authenticated admin session.
    """
    # Login to create session
    response = test_client.post("/login", data={
        "email": test_admin.email,
        "password": "adminpassword123"
    }, follow_redirects=False)
    
    return test_client
