from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from src.schemas import ContactCreate, UserModel
from tests.conftest import client


def test_create_contact(client):
    response = client.post("/signup/", json={"username": "user@example.com", "password": "password"})
    assert response.status_code == 201

    response = client.post("/login", data={"username": "user@example.com", "password": "password"})
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    response = client.post("/contacts/", json={
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "phone_number": "1234567890"
    }, headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 201
    assert response.json()["email"] == "johndoe@example.com"


def test_read_contacts(client):
    response = client.post("/login", data={"username": "user@example.com", "password": "password"})
    assert response.status_code == 200
    access_token = response.json()["access_token"]

    response = client.get("/contacts/", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert len(response.json()) > 0
