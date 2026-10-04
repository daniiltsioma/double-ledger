from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from database import SessionLocal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from models import Account, Entry, Transaction

class AccountCreate(BaseModel):
    name: str

class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    description: str
    amount: int = Field(gt=0)

    @model_validator(mode="after")
    def check_accounts_differ(self):
        if self.from_account_id == self.to_account_id:
            raise ValueError("accounts must differ")
        return self

class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account_id: int
    amount: int

class TransferOut(BaseModel):
    transaction_id: int
    description: str
    entries: list[EntryOut]

app = FastAPI()

def get_db():
    with SessionLocal() as session:
        yield session

@app.get("/accounts/{account_id}")
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    balance = db.scalar(
        select(func.coalesce(func.sum(Entry.amount), 0)).where(Entry.account_id == account_id)
    )
    return {"id": account.id, "name": account.name, "balance": balance}

@app.post("/accounts", status_code=201)
def post_account(account_in: AccountCreate, db: Session = Depends(get_db)):
    account = Account(name=account_in.name) 
    db.add(account)
    db.commit()
    return {"id": account.id, "name": account.name}

@app.post("/transfers", status_code=201, response_model=TransferOut)
def post_transfer(transfer_in: TransferCreate, db: Session = Depends(get_db)):
    account_from = db.get(Account, transfer_in.from_account_id)
    if account_from is None:
        raise HTTPException(status_code=422, detail=f"Account {transfer_in.from_account_id} does not exist")
    account_to = db.get(Account, transfer_in.to_account_id)
    if account_to is None:
        raise HTTPException(status_code=422, detail=f"Account {transfer_in.to_account_id} does not exist")
    transaction = Transaction(description=transfer_in.description)
    db.add(transaction)
    db.flush()
    from_entry = Entry(
        transaction_id=transaction.id, 
        account_id=account_from.id, 
        amount=-transfer_in.amount)
    to_entry = Entry(
        transaction_id=transaction.id, 
        account_id=account_to.id, 
        amount=transfer_in.amount)
    db.add_all([from_entry, to_entry])
    db.commit()
    return TransferOut(
        transaction_id=transaction.id,
        description=transaction.description,
        entries=[from_entry, to_entry]
    )