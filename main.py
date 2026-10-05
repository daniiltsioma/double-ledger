from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from database import SessionLocal

from models import Account, Entry
from schemas import AccountCreate, TransferCreate, TransferOut
from services import AccountNotFound, InsuffientFunds, create_transfer, get_balance

app = FastAPI()

def get_db():
    with SessionLocal() as session:
        yield session

@app.get("/accounts/{account_id}")
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    balance = get_balance(db, account_id)
    return {
        "id": account.id, 
        "name": account.name, 
        "balance": balance,
        "allow_overdraft": account.allow_overdraft
    }

@app.post("/accounts", status_code=201)
def post_account(account_in: AccountCreate, db: Session = Depends(get_db)):
    account = Account(name=account_in.name, allow_overdraft=account_in.allow_overdraft or False) 
    db.add(account)
    db.commit()
    return {"id": account.id, "name": account.name}

@app.post("/transfers", status_code=201, response_model=TransferOut)
def post_transfer(transfer_in: TransferCreate, db: Session = Depends(get_db)):
    try:
        transaction, entries = create_transfer(db, transfer_in.from_account_id, transfer_in.to_account_id, transfer_in.amount, transfer_in.description)
    except AccountNotFound as e:
        raise HTTPException(status_code=422, detail=str(e))
    except InsuffientFunds as e:
        raise HTTPException(status_code=409, detail=str(e))
    
    return TransferOut(
        transaction_id=transaction.id,
        description=transaction.description,
        entries=entries
    )