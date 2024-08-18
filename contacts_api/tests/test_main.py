from sqlalchemy.orm import Session
from conftest import client


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_signup(client):
    response = client.post("/signup", json={"username": "test@example.com", "password": "testpassword"})
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert "message" in response.json()


def test_login(client):
    response = client.post("/login", data={"username": "test@example.com", "password": "testpassword"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
