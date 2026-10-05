from sqlalchemy import func, select

from models import Account, Entry, Transaction


class LedgerError(Exception):
    """Base class for business rule violation."""

class AccountNotFound(LedgerError):
    def __init__(self, account_id: int):
        super().__init__(f"Account {account_id} does not exist")

class InsuffientFunds(LedgerError):
    def __init__(self, account_id: int):
        super().__init__(f"Account {account_id} does has insufficient funds to process the transfer")

def get_balance(db, account_id):
    balance = db.scalar(
        select(func.coalesce(func.sum(Entry.amount), 0)).where(Entry.account_id == account_id)
    )
    return balance

def create_transfer(db, from_account_id, to_account_id, amount, description):
    account_from = db.get(Account, from_account_id)
    if account_from is None:
        raise AccountNotFound(from_account_id)

    if not account_from.allow_overdraft and get_balance(db, account_from.id) < amount:
        raise InsuffientFunds(account_from.id)

    account_to = db.get(Account, to_account_id)
    if account_to is None:
        raise AccountNotFound(to_account_id)

    transaction = Transaction(description=description)
    db.add(transaction)
    db.flush()
    from_entry = Entry(
        transaction_id=transaction.id, 
        account_id=account_from.id, 
        amount=-amount)
    to_entry = Entry(
        transaction_id=transaction.id, 
        account_id=account_to.id, 
        amount=amount)
    db.add_all([from_entry, to_entry])
    db.commit()

    return transaction, [from_entry, to_entry]
