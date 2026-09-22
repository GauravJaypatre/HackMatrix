"""
inspect_and_clean.py — IBM AML HI-Small Transaction Data Inspector & Cleaner
=============================================================================
Reads the raw HI-Small_Trans.csv, inspects columns/types, writes SCHEMA.md
with a 10-row sample preview, and produces transactions_clean.csv with
standardized column names.

Usage:
    python inspect_and_clean.py

Expects:
    data/ibm_aml/HI-Small_Trans.csv

Produces:
    data/ibm_aml/transactions_clean.csv
    data/ibm_aml/SCHEMA.md
"""

import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).parent
RAW_FILE = SCRIPT_DIR / "HI-Small_Trans.csv"
CLEAN_FILE = SCRIPT_DIR / "transactions_clean.csv"
SCHEMA_FILE = SCRIPT_DIR / "SCHEMA.md"


def main():
    print("=" * 70)
    print("IBM AML HI-Small Transaction Data Inspector")
    print("=" * 70)
    print()

    if not RAW_FILE.exists():
        print(f"ERROR: {RAW_FILE} not found.")
        print("Please download HI-Small_Trans.csv from Kaggle and place it here.")
        sys.exit(1)

    # ─── Read raw data ────────────────────────────────────────────────────
    print(f"[1/4] Reading {RAW_FILE.name}...")
    df = pd.read_csv(RAW_FILE, low_memory=False)
    print(f"  Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print()

    # ─── Inspect columns ─────────────────────────────────────────────────
    print("[2/4] Column inspection:")
    col_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = df[col].notna().sum()
        null_pct = (1 - non_null / len(df)) * 100
        nunique = df[col].nunique()
        sample_val = str(df[col].dropna().iloc[0]) if non_null > 0 else "N/A"
        if len(sample_val) > 50:
            sample_val = sample_val[:50] + "..."
        col_info.append({
            "column": col,
            "dtype": dtype,
            "non_null": non_null,
            "null_pct": f"{null_pct:.1f}%",
            "unique": nunique,
            "sample": sample_val,
        })
        print(f"  {col:30s}  {dtype:15s}  nulls={null_pct:5.1f}%  unique={nunique:,}")

    print()

    # ─── Standardize column names ─────────────────────────────────────────
    print("[3/4] Standardizing column names...")
    # Build rename map: lowercase, replace spaces with underscores, strip whitespace
    rename_map = {}
    for col in df.columns:
        new_name = col.strip().lower().replace(" ", "_").replace("-", "_")
        # Common renames for this dataset
        rename_map[col] = new_name

    # Explicit overrides for the duplicate "Account" columns
    rename_map["Account"] = "from_account"
    rename_map["Account.1"] = "to_account"

    df_clean = df.rename(columns=rename_map)
    print("  Column mapping:")
    for old, new in rename_map.items():
        marker = " (*)" if old != new else ""
        print(f"    {old:30s} -> {new}{marker}")

    # Add stable transaction_id as first column
    df_clean.insert(0, "transaction_id",
                    [f"TXN_{i:07d}" for i in range(1, len(df_clean) + 1)])
    print(f"  Added transaction_id column: TXN_0000001 .. TXN_{len(df_clean):07d}")

    # Save clean version
    df_clean.to_csv(CLEAN_FILE, index=False)
    print(f"\n  Saved -> {CLEAN_FILE.name} ({len(df_clean):,} rows)")

    # ─── Write SCHEMA.md ─────────────────────────────────────────────────
    print("\n[4/4] Writing SCHEMA.md...")

    # 10-row sample
    sample_df = df.head(10)
    sample_md = sample_df.to_markdown(index=False)

    # Build clean column table
    clean_col_info = []
    for old, new in rename_map.items():
        orig = next(c for c in col_info if c["column"] == old)
        clean_col_info.append({
            "original_name": old,
            "clean_name": new,
            "dtype": orig["dtype"],
            "null_pct": orig["null_pct"],
            "unique_values": orig["unique"],
            "sample": orig["sample"],
        })

    schema_content = f"""# IBM AML HI-Small Transactions -- Schema Documentation

## Source
- **Dataset**: IBM Transactions for Anti Money Laundering (AML)
- **Variant**: HI-Small (High Illicit, Small)
- **URL**: https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml

## Raw File: HI-Small_Trans.csv
- **Rows**: {len(df):,}
- **Columns**: {len(df.columns)}

## Column Schema

| Original Column | Clean Column | Data Type | Null % | Unique Values | Sample Value |
|-----------------|-------------|-----------|--------|---------------|-------------|
| *(added)* | `transaction_id` | `object` | 0.0% | {len(df_clean):,} | `TXN_0000001` |
"""
    for c in clean_col_info:
        schema_content += (
            f"| `{c['original_name']}` | `{c['clean_name']}` | "
            f"`{c['dtype']}` | {c['null_pct']} | {c['unique_values']:,} | "
            f"`{c['sample']}` |\n"
        )

    schema_content += f"""
## Clean File: transactions_clean.csv

Standardized version with lowercase snake_case column names plus a stable
`transaction_id` column. Same data, no rows removed. {len(df_clean):,} rows,
{len(df_clean.columns)} columns.

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

Stable sequential identifier (`TXN_0000001` through `TXN_{len(df_clean):07d}`)
added during cleaning. Deterministic — same input always produces the same IDs.
Used by `data/synthetic_hr/injected_transactions.csv` and
`labeled_scenarios.related_transaction_ids` to reference specific rows.

Synthetic (injected) transactions use the prefix `SYN_` to avoid collisions
with real transaction IDs.

## 10-Row Sample Preview

{sample_md}

## Notes
- The `is_laundering` column is the **ground truth label**.
  A value of `1` indicates the transaction is part of a synthetic money
  laundering pattern; `0` indicates a legitimate transaction.
- `from_account` / `to_account` are the join keys used by the synthetic HR
  layer (`data/synthetic_hr/`).
- Companion file `HI-Small_Patterns.txt` lists the specific laundering
  patterns (fan-out, fan-in, cycle, etc.) with their constituent transactions.
"""

    with open(SCHEMA_FILE, "w", encoding="utf-8") as f:
        f.write(schema_content)

    print(f"  Saved -> {SCHEMA_FILE.name}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
