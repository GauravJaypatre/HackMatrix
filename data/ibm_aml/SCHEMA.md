# IBM AML HI-Small Transactions -- Schema Documentation

## Source
- **Dataset**: IBM Transactions for Anti Money Laundering (AML)
- **Variant**: HI-Small (High Illicit, Small)
- **URL**: https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml

## Raw File: HI-Small_Trans.csv
- **Rows**: 5,078,345
- **Columns**: 11

## Column Schema

| Original Column | Clean Column | Data Type | Null % | Unique Values | Sample Value |
|-----------------|-------------|-----------|--------|---------------|-------------|
| *(added)* | `transaction_id` | `object` | 0.0% | 5,078,345 | `TXN_0000001` |
| `Timestamp` | `timestamp` | `object` | 0.0% | 15,018 | `2022/09/01 00:20` |
| `From Bank` | `from_bank` | `int64` | 0.0% | 30,470 | `10` |
| `Account` | `from_account` | `object` | 0.0% | 496,995 | `8000EBD30` |
| `To Bank` | `to_bank` | `int64` | 0.0% | 15,811 | `10` |
| `Account.1` | `to_account` | `object` | 0.0% | 420,636 | `8000EBD30` |
| `Amount Received` | `amount_received` | `float64` | 0.0% | 915,161 | `3697.34` |
| `Receiving Currency` | `receiving_currency` | `object` | 0.0% | 15 | `US Dollar` |
| `Amount Paid` | `amount_paid` | `float64` | 0.0% | 923,873 | `3697.34` |
| `Payment Currency` | `payment_currency` | `object` | 0.0% | 15 | `US Dollar` |
| `Payment Format` | `payment_format` | `object` | 0.0% | 7 | `Reinvestment` |
| `Is Laundering` | `is_laundering` | `int64` | 0.0% | 2 | `0` |

## Clean File: transactions_clean.csv

Standardized version with lowercase snake_case column names plus a stable
`transaction_id` column. Same data, no rows removed. 5,078,345 rows,
12 columns.

## Sender / Receiver Columns

Each transaction has a **sender** (originator) and a **receiver** (beneficiary),
identified by a bank + account pair:

| Role | Bank Column | Account Column | Description |
|------|-------------|----------------|-------------|
| **Sender** | `from_bank` | `from_account` | The originating bank and account that initiates/pays the transaction |
| **Receiver** | `to_bank` | `to_account` | The destination bank and account that receives the funds |

> **Note on raw column names:** The raw CSV has two columns both named `Account`.
> Pandas loads these as `Account` and `Account.1`. In `transactions_clean.csv`
> they are renamed to `from_account` and `to_account` respectively for clarity.

## `transaction_id` Column

Stable sequential identifier (`TXN_0000001` through `TXN_5078345`)
added during cleaning. Deterministic — same input always produces the same IDs.
Used by `data/synthetic_hr/injected_transactions.csv` and
`labeled_scenarios.related_transaction_ids` to reference specific rows.

Synthetic (injected) transactions use the prefix `SYN_` to avoid collisions
with real transaction IDs.

## 10-Row Sample Preview

| Timestamp        |   From Bank | Account   |   To Bank | Account.1   |   Amount Received | Receiving Currency   |   Amount Paid | Payment Currency   | Payment Format   |   Is Laundering |
|:-----------------|------------:|:----------|----------:|:------------|------------------:|:---------------------|--------------:|:-------------------|:-----------------|----------------:|
| 2022/09/01 00:20 |          10 | 8000EBD30 |        10 | 8000EBD30   |           3697.34 | US Dollar            |       3697.34 | US Dollar          | Reinvestment     |               0 |
| 2022/09/01 00:20 |        3208 | 8000F4580 |         1 | 8000F5340   |              0.01 | US Dollar            |          0.01 | US Dollar          | Cheque           |               0 |
| 2022/09/01 00:00 |        3209 | 8000F4670 |      3209 | 8000F4670   |          14675.6  | US Dollar            |      14675.6  | US Dollar          | Reinvestment     |               0 |
| 2022/09/01 00:02 |          12 | 8000F5030 |        12 | 8000F5030   |           2806.97 | US Dollar            |       2806.97 | US Dollar          | Reinvestment     |               0 |
| 2022/09/01 00:06 |          10 | 8000F5200 |        10 | 8000F5200   |          36683    | US Dollar            |      36683    | US Dollar          | Reinvestment     |               0 |
| 2022/09/01 00:03 |           1 | 8000F5AD0 |         1 | 8000F5AD0   |           6162.44 | US Dollar            |       6162.44 | US Dollar          | Reinvestment     |               0 |
| 2022/09/01 00:08 |           1 | 8000EBAC0 |         1 | 8000EBAC0   |             14.26 | US Dollar            |         14.26 | US Dollar          | Reinvestment     |               0 |
| 2022/09/01 00:16 |           1 | 8000EC1E0 |         1 | 8000EC1E0   |             11.86 | US Dollar            |         11.86 | US Dollar          | Reinvestment     |               0 |
| 2022/09/01 00:26 |          12 | 8000EC280 |      2439 | 8017BF800   |              7.66 | US Dollar            |          7.66 | US Dollar          | Credit Card      |               0 |
| 2022/09/01 00:21 |           1 | 8000EDEC0 |    211050 | 80AEF5310   |            383.71 | US Dollar            |        383.71 | US Dollar          | Credit Card      |               0 |

## Notes
- The `is_laundering` column is the **ground truth label**.
  A value of `1` indicates the transaction is part of a synthetic money
  laundering pattern; `0` indicates a legitimate transaction.
- `from_account` / `to_account` are the join keys used by the synthetic HR
  layer (`data/synthetic_hr/`).
- Companion file `HI-Small_Patterns.txt` lists the specific laundering
  patterns (fan-out, fan-in, cycle, etc.) with their constituent transactions.
