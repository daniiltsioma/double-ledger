import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from main import app, get_db

engine = create_engine(os.getenv("TEST_DB_STRING"))
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    with TestingSessionLocal() as session:
        yield session

@pytest.fixture(autouse=True)
def clean_tables():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE entries, transactions, accounts RESTART IDENTITY"))
    yield

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def db():
    with TestingSessionLocal() as session:
        yield session