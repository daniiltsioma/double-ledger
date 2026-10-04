CREATE TABLE accounts (
    id INT PRIMARY KEY,
    name VARCHAR(20),
    created_at TIMESTAMP
)

CREATE TABLE transactions (
    id PRIMARY KEY,
    description VARCHAR(50),
    created_at TIMESTAMP
)

CREATE TABLE entries (
    id PRIMARY KEY,
    transaction_id INT,
    account_id INT,
    amount DECIMAL(10, 2),

    CONSTRAINT fk_entry_transaction FOREIGN KEY (transaction_id) REFERENCES (transactions),
    CONSTRAINT fk_entry_account FOREIGN KEY (account_id) REFERENCES (accounts)
)

-- balance of single account with ID = 123
select sum(e.amount)
from entries e join accounts a on e.account_id = a.account_id
where account_id = 123;