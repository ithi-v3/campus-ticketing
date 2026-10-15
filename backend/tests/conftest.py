"""Tests run against a real Postgres database because the triggers, view and
function are part of what is being tested. Point TEST_DATABASE_URL at an empty
throwaway database whose name contains 'test' -- it is wiped on every run."""
import os

import pytest
from sqlalchemy import create_engine, text

from app import create_app

SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "database")


def _test_url():
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    if "test" not in url.rsplit("/", 1)[-1]:
        pytest.fail("TEST_DATABASE_URL must point at a database with 'test' in its name")
    return url.replace("postgres://", "postgresql://", 1)


@pytest.fixture(scope="session")
def database():
    url = _test_url()
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        for name in ("01_schema.sql", "02_seed.sql", "03_demo_data.sql"):
            with open(os.path.join(SQL_DIR, name), encoding="utf-8") as fh:
                cur.execute(fh.read())
        raw.commit()
    finally:
        raw.close()
    engine.dispose()
    return url


@pytest.fixture()
def app(database):
    return create_app({"TESTING": True, "JWT_SECRET": "test-secret",
                       "SQLALCHEMY_DATABASE_URI": database})


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": "Bearer " + res.get_json()["token"]}


@pytest.fixture()
def student(client):
    return login(client, "divya@campus.test", "Student@123")


@pytest.fixture()
def other_student(client):
    return login(client, "karthik@campus.test", "Student@123")


@pytest.fixture()
def technician(client):
    return login(client, "ravi.tech@campus.test", "Tech@123")


@pytest.fixture()
def admin(client):
    return login(client, "admin@campus.test", "Admin@123")
