import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_pages_public_when_auth_disabled(client):
    assert client.get("/server").status_code == 200
    assert client.get("/models").status_code == 200
    assert client.get("/health").status_code == 200


def test_auth_redirects_html_pages(client, monkeypatch):
    monkeypatch.setattr("app.auth.WEB_TOKEN", "secret")
    response = client.get("/server", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["location"]


def test_auth_returns_401_for_api(client, monkeypatch):
    monkeypatch.setattr("app.auth.WEB_TOKEN", "secret")
    response = client.get("/api/server/status", follow_redirects=False)
    assert response.status_code == 401


def test_login_with_valid_token(client, monkeypatch):
    monkeypatch.setattr("app.auth.WEB_TOKEN", "secret")
    response = client.post("/login", data={"token": "secret"}, follow_redirects=False)
    assert response.status_code == 303
    assert client.get("/server", follow_redirects=False).status_code == 200


def test_login_with_wrong_token(client, monkeypatch):
    monkeypatch.setattr("app.auth.WEB_TOKEN", "secret")
    response = client.post("/login", data={"token": "wrong"}, follow_redirects=False)
    assert response.status_code == 401


def test_logout_clears_session(client, monkeypatch):
    monkeypatch.setattr("app.auth.WEB_TOKEN", "secret")
    client.post("/login", data={"token": "secret"}, follow_redirects=False)
    assert client.get("/server", follow_redirects=False).status_code == 200
    client.post("/logout", follow_redirects=False)
    assert client.get("/server", follow_redirects=False).status_code == 302
