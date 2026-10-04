from pydantic import BaseModel, ConfigDict, Field, model_validator

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
