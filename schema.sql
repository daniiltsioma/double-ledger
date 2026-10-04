CREATE TABLE if not exists accounts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE if not exists transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE if not exists entries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id INT NOT NULL,
    account_id INT NOT NULL,
    amount bigint NOT NULL,

    constraint check_amount check(amount <> 0),

    CONSTRAINT fk_entry_transaction FOREIGN KEY (transaction_id) REFERENCES transactions (id),
    CONSTRAINT fk_entry_account FOREIGN KEY (account_id) REFERENCES accounts (id)
);

create index idx_account_id on entries (account_id);
