-- HSBC WhatsApp Banking Assistant — Database Schema

CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    account_number VARCHAR(30) UNIQUE NOT NULL,
    account_holder VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    account_type VARCHAR(50) DEFAULT 'current',
    balance DECIMAL(15, 2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'GBP',
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    transaction_type VARCHAR(50),
    amount DECIMAL(15, 2),
    description TEXT,
    reference VARCHAR(100),
    balance_after DECIMAL(15, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE,
    last_active TIMESTAMP DEFAULT NOW(),
    total_messages INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed data — 3 test accounts
INSERT INTO accounts (account_number, account_holder, phone_number, account_type, balance, currency) VALUES
('GB12HSBC00010001234567', 'John Smith', '447812345678', 'current', 2543.67, 'GBP'),
('GB12HSBC00010007654321', 'Sarah Johnson', '447987654321', 'savings', 15750.00, 'GBP'),
('GB12HSBC00010009876543', 'Michael Brown', '447123456789', 'current', 892.34, 'GBP');

-- Transactions for John Smith
INSERT INTO transactions (account_id, transaction_type, amount, description, reference, balance_after) VALUES
(1, 'debit', 45.99, 'Tesco Superstore', 'POS-TES-001', 2497.68),
(1, 'credit', 2500.00, 'Salary Payment - ABC Ltd', 'SAL-JULY-2026', 4997.68),
(1, 'debit', 1200.00, 'Rent Payment', 'SO-RENT-001', 3797.68),
(1, 'debit', 89.50, 'British Gas', 'DD-GAS-001', 3708.18),
(1, 'debit', 1164.51, 'HMRC Tax Payment', 'REF-HMRC-001', 2543.67);

-- Transactions for Sarah Johnson
INSERT INTO transactions (account_id, transaction_type, amount, description, reference, balance_after) VALUES
(2, 'credit', 500.00, 'Transfer from Current Account', 'TRF-001', 15750.00),
(2, 'credit', 250.00, 'Interest Payment', 'INT-JULY-2026', 15250.00),
(2, 'debit', 200.00, 'Transfer to Current Account', 'TRF-002', 15000.00),
(2, 'credit', 1000.00, 'Bonus Payment', 'BON-001', 15200.00),
(2, 'debit', 300.00, 'ISA Transfer', 'ISA-001', 14200.00);

-- Transactions for Michael Brown
INSERT INTO transactions (account_id, transaction_type, amount, description, reference, balance_after) VALUES
(3, 'credit', 1800.00, 'Salary Payment', 'SAL-JULY-2026', 2692.34),
(3, 'debit', 750.00, 'Rent Payment', 'SO-RENT-002', 1942.34),
(3, 'debit', 65.00, 'Sky TV', 'DD-SKY-001', 1877.34),
(3, 'debit', 45.00, 'Council Tax', 'DD-CT-001', 1832.34),
(3, 'debit', 940.00, 'Credit Card Payment', 'CC-PAY-001', 892.34);