# Canonical Entity Tables — Schema Documentation

Master entity tables for the investigation universe connecting accounts, customers, employees, and transactions.

---

## 1. accounts.csv (`data/entities/accounts.csv`)

Scoped to the 1,884 accounts that participate anywhere in the synthetic HR layer or scenario data (access events, labeled scenarios, injected transactions, and customer accounts).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `account_id` | string | No | Unique account identifier (IBM AML format e.g. `800056370`) |
| `linked_customer_id` | string | Yes | Customer ID owning this account (empty if unknown/external) |
| `bank_id` | int | No | Bank identifier from `transactions_clean.csv` / `injected_transactions.csv` |
| `first_seen_timestamp` | string | No | Earliest transaction timestamp (`YYYY/MM/DD HH:MM`) |
| `last_seen_timestamp` | string | No | Latest transaction timestamp (`YYYY/MM/DD HH:MM`) |
| `real_txn_count` | int | No | Number of real transactions in `transactions_clean.csv` where account is sender or receiver |
| `synthetic_txn_count` | int | No | Number of injected transactions where account is sender or receiver |
| `total_transaction_count` | int | No | Sum of `real_txn_count` + `synthetic_txn_count` |
| `background_real_laundering_count` | int | No | Count of real (non-synthetic) background transactions with `is_laundering=1` |

> ⚠️ **Evaluation Caveat for Detection (Member 2)**:
> In the IBM AML dataset, real accounts carry their own background transaction histories, which in some cases include pre-existing illicit transactions (`is_laundering=1`). Any real laundering transactions present in an account's background ledger are **NOT** part of that scenario's injected ground truth and must **NOT** be counted when Member 2 computes scenario-level detection recall or false-positive rate for that specific scenario. Only transactions listed in `related_transaction_ids` define that scenario's ground truth outcome.

---

## 2. customers.csv (`data/entities/customers.csv`)

Scoped to the 939 unique customer IDs appearing in `employee_customer_map.csv` or `profile_changes.csv`.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `customer_id` | string | No | Unique customer identifier |
| `name` | string | No | Synthetic customer name (Faker generated, seed=42) |
| `country` | string | No | Synthetic customer country (Faker generated, seed=42) |
| `account_ids` | string | No | Comma-separated list of account IDs linked to this customer |
| `risk_rating` | string | No | Synthetic risk level: `Low`, `Medium`, or `High` |

> ⚠️ **Note on `risk_rating`**: This field is generated synthetically (weighted: 75% Low, 20% Medium, 5% High) for demo, investigation UI, and baseline risk simulation. It is NOT derived from any real financial or KYC signal.

---

## 3. Architectural Clarifications & Modeling Constraints

### 3.1 1:1 Customer-to-Account Mapping
In this dataset, each `customer_id` is identical to its primary `account_id` (a strict 1:1 mapping). This is an intentional architectural simplification because the upstream IBM AML dataset contains transaction records with only account identifiers (`from_account`, `to_account`) and does not define a separate customer/KYC entity layer. Downstream detection (Member 2) and backend/evidence teams (Member 3) must **not** assume 1-to-many customer-account hierarchies exist in this data.

### 3.2 Dual Audit System Logging (Access Events vs Profile Changes)
For correlated scenarios (e.g. S01), administrative actions such as limit elevations are logged across two separate simulated systems at the exact same timestamp:
1. **Core Banking / System Access Log (`access_events.csv`)**: Technical privilege and permission modifications on the account (e.g. `action="modify"`, `old_value="transfer_limit=10000"`, `new_value="transfer_limit=100000"`).
2. **CRM / Customer Profile Audit Trail (`profile_changes.csv`)**: Customer profile attribute changes (e.g. `field_changed="spending_limit"`, `old_value="10000"`, `new_value="100000"`).

> ⚠️ **Critical Guidance for Detection Rules (Member 2)**:
> This reflects real-world dual logging where a single administrative operation leaves traces in both IT access logs and CRM audit trails. When computing detection features or triggering alert rules in Part 4, these co-occurring records must be collapsed into **one single underlying signal (`privilege_change`)**, rather than counted as two independent corroborating pieces of evidence.

### 3.3 Transaction Count Accounting & Self-Transfers
In the IBM AML dataset, certain transactions are self-transfers (e.g. internal reinvestment, certificate renewals, or automated balancing) where `from_account == to_account`. 
In `accounts.csv`, `real_txn_count` represents the count of **distinct transaction rows** involving the account ($|\text{From} \cup \text{To}| = |\text{From}| + |\text{To}| - |\text{From} \cap \text{To}|$). Self-transfers are counted once per row to ensure 100% exact reconciliation between the Account Master Record and the Transaction Ledger.
