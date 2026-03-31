from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_user():
    response = client.post("/users", json={"name": "Alice"})
    assert response.status_code == 200
    assert response.json()["name"] == "Alice"

def test_list_users():
    response = client.get("/users")
    assert response.status_code == 200