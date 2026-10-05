def test_create_account(client):
    response = client.post("/accounts", json={"name": "Alice"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alice"
    assert isinstance(body["id"], int)

def test_create_account_requires_name(client):
    response = client.post("/accounts", json={})
    assert response.status_code == 422


def test_new_account_has_zero_balance(client):
    account_id = client.post("/accounts", json={"name": "Alice"}).json()["id"]
    response = client.get(f"/accounts/{account_id}")
    assert response.status_code == 200
    assert response.json()["balance"] == 0

def test_get_missing_account_returns_404(client):
    response = client.get("/accounts/999")
    assert response.status_code == 404