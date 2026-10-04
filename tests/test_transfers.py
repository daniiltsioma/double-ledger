import pytest
from sqlalchemy import func, select

from models import Entry, Transaction

def make_account(client, name):
    return client.post("/accounts", json={"name": name}).json()["id"]

def test_transfer_moves_money(client):
    alice = make_account(client, "Alice")
    shop = make_account(client, "7-Eleven")

    response = client.post("/transfers", json={
        "from_account_id": alice,
        "to_account_id": shop,
        "amount": 349,
        "description": "Red Bull"
    })

    assert response.status_code == 201
    assert client.get(f"/accounts/{alice}").json()["balance"] == -349
    assert client.get(f"/accounts/{shop}").json()["balance"] == 349

@pytest.mark.parametrize("amount", [0, -100])
def test_transfer_rejects_non_positive_amount(client, amount):
    alice = make_account(client, "Alice")
    shop = make_account(client, "7-Eleven")

    response = client.post("/transfers", json={
        "from_account_id": alice,
        "to_accound_id": shop,
        "amount": amount,
        "description": "Bad transfer"
    })

    assert response.status_code == 422

def test_transfer_to_missing_account_writes_nothing(client, db):
    alice = make_account(client, "Alice")

    response = client.post("/transfers", json={
        "from_account_id": alice,
        "to_accound_id": 999,
        "amount": 349,
        "description": "Nowhere"
    })

    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(Transaction)) == 0
    assert db.scalar(select(func.count()).select_from(Entry)) == 0

def test_transfer_from_account_to_itself_forbidden(client):
    alice = make_account(client, "Alice")

    response = client.post("/transfers", json={
        "from_account_id": alice,
        "to_accound_id": alice,
        "amount": 349,
        "description": "Forbidden"
    })

    assert response.status_code == 422
    
def test_transfer_from_nonexistent_account_writes_nothing(client, db):
    alice = make_account(client, "Alice")

    response = client.post("/transfers", json={
        "from_account_id": 999,
        "to_accound_id": alice,
        "amount": 349,
        "description": "sender non-existent"
    })

    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(Transaction)) == 0
    assert db.scalar(select(func.count()).select_from(Entry)) == 0

def test_transfer_leaves_money_balanced(client, db):
    alice = make_account(client, "Alice") 
    john = make_account(client, "John") 
    susan = make_account(client, "Susan") 

    response = client.post("/transfers", json={
        "from_account_id": alice,
        "to_accound_id": john,
        "amount": 349,
        "description": "transfer 1"
    })

    response = client.post("/transfers", json={
        "from_account_id": john,
        "to_accound_id": susan,
        "amount": 239,
        "description": "transfer 2"
    })

    response = client.post("/transfers", json={
        "from_account_id": susan,
        "to_accound_id": john,
        "amount": 3499,
        "description": "transfer 3"
    })

    response = client.post("/transfers", json={
        "from_account_id": alice,
        "to_accound_id": susan,
        "amount": 99,
        "description": "transfer 4"
    })

    response = client.post("/transfers", json={
        "from_account_id": alice,
        "to_accound_id": john,
        "amount": 1349,
        "description": "transfer 1"
    })

    alice_balance = client.get(f"/accounts/{alice}").json()["balance"]
    john_balance = client.get(f"/accounts/{john}").json()["balance"]
    susan_balance = client.get(f"/accounts/{susan}").json()["balance"]

    assert alice_balance + john_balance + susan_balance == 0