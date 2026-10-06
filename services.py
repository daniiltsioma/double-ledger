import hashlib
import json
from uuid import UUID
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from models import Account, Entry, IdempotencyKey, Transaction


class LedgerError(Exception):
    """Base class for business rule violation."""

class AccountNotFound(LedgerError):
    def __init__(self, account_id: int):
        super().__init__(f"Account {account_id} does not exist")

class InsuffientFunds(LedgerError):
    def __init__(self, account_id: int):
        super().__init__(f"Account {account_id} has insufficient funds to process the transfer")

class TransactionNotFound(LedgerError):
    def __init__(self, transaction_id: int):
        super().__init__(f"Transaction {transaction_id} does not exist")

class ReversingAReversal(LedgerError):
    def __init__(self, transaction_id: int):
        super().__init__(f"Transaction {transaction_id} cannot might be reversed since it reverses another transaction.")

class AlreadyReversed(LedgerError):
    def __init__(self, transaction_id: int):
        super().__init__(f"Transaction {transaction_id} has already been reversed.")

class IdempotencyKeyReused(LedgerError):
    def __init__(self, idempotency_key: uuid.UUID):
        super().__init__(f"Idempotency key {idempotency_key} reused for a different request")

def get_balance(db, account_id):
    balance = db.scalar(
        select(func.coalesce(func.sum(Entry.amount), 0)).where(Entry.account_id == account_id)
    )
    return balance

def create_transfer(db, from_account_id, to_account_id, amount, description, idempotency_key: UUID):
    existing_key = db.get(IdempotencyKey, idempotency_key)
    if existing_key is not None:
        if hashlib.sha256(json.dumps({
                from_account_id: from_account_id,
                to_account_id: to_account_id,
                amount: amount,
                description: description  
            }).encode("utf-8")).hexdigest() == existing_key.request_hash:
            transaction = db.get(Transaction, existing_key.transaction_id)
            entries = db.scalars(select(Entry).where(Entry.transaction_id == transaction.id)).all()
            return transaction, entries
        else:
            raise IdempotencyKeyReused(idempotency_key)
            
    account_from = db.get(Account, from_account_id)
    if account_from is None:
        raise AccountNotFound(from_account_id)

    account_to = db.get(Account, to_account_id)
    if account_to is None:
        raise AccountNotFound(to_account_id)

    if not account_from.allow_overdraft and get_balance(db, account_from.id) < amount:
        raise InsuffientFunds(account_from.id)

    transaction = Transaction(description=description)
    db.add(transaction)
    db.flush()
    new_key = IdempotencyKey(
        transaction_id=transaction.id,
        key=idempotency_key,
        request_hash=hashlib.sha256(json.dumps({
            from_account_id: from_account_id,
            to_account_id: to_account_id,
            amount: amount,
            description: description  
        }).encode("utf-8")).hexdigest()
    )
    db.add(new_key)
    from_entry = Entry(
        transaction_id=transaction.id, 
        account_id=account_from.id, 
        amount=-amount)
    to_entry = Entry(
        transaction_id=transaction.id, 
        account_id=account_to.id, 
        amount=amount)
    db.add_all([from_entry, to_entry])
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        if e.orig.diag.constraint_name == "idempotency_keys_pkey":
            existing_key = db.get(IdempotencyKey, idempotency_key)
            if hashlib.sha256(json.dumps({
                    from_account_id: from_account_id,
                    to_account_id: to_account_id,
                    amount: amount,
                    description: description  
                }).encode("utf-8")).hexdigest() == existing_key.request_hash:
                    transaction = db.get(Transaction, existing_key.transaction_id)
                    entries = db.scalars(select(Entry).where(Entry.transaction_id == transaction.id)).all()
                    return transaction, entries
            else:
                raise IdempotencyKeyReused(idempotency_key)
        else:
            raise e

    return transaction, [from_entry, to_entry]

def create_reversal(db, transaction_id):
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise TransactionNotFound(transaction_id)

    if transaction.reverses_transaction_id != None:
        raise ReversingAReversal(transaction_id)
    
    if db.scalar(select(Transaction).where(Transaction.reverses_transaction_id == transaction_id)):
        raise AlreadyReversed(transaction_id)
    
    entries = db.scalars(select(Entry).where(Entry.transaction_id == transaction_id)).all()

    reversal = Transaction(
        description=f"Reverse transaction {transaction.id}",
        reverses_transaction_id=transaction.id
    )
    db.add(reversal)
    db.flush()
    reversal_entries = []
    for entry in entries:
        reversal_entries.append(Entry(
            transaction_id=reversal.id,
            account_id=entry.account_id,
            amount=-entry.amount
        ))
    db.add_all(reversal_entries)
    db.commit()

    return reversal, reversal_entries