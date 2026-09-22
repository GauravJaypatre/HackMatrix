"""
generate_amlsim.py — Custom Generator Implementing AMLSim's Alert-Pattern Methodology
======================================================================================
NOTE: This is NOT actual AMLSim output. This is a custom Python generator that
implements the same alert-pattern types (cycle, fan-out, fan-in, gather-scatter)
as IBM's AMLSim simulator, producing transaction data with the same schema and
ground-truth labeling. This avoids AMLSim's heavy Java/legacy-Python dependencies
while producing functionally equivalent output for downstream graph analysis.

Reference: https://github.com/IBM/AMLSim

Usage:
    python generate_amlsim.py

Output files (in the same directory as this script):
    - accounts.csv       — account metadata
    - transactions.csv   — individual transactions with alert membership flags
    - alert_patterns.csv — summary of each generated alert pattern
    - alert_members.csv  — mapping of accounts to their roles in each pattern

Random seed is fixed for full reproducibility.
"""

import os
import random
import csv
from datetime import datetime, timedelta
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────
SEED = 42
NUM_ACCOUNTS = 2000
SIM_DAYS = 45  # 45-day simulation period
NUM_NORMAL_TX = 8000  # background normal transactions

# Alert pattern counts (how many instances of each pattern to generate)
PATTERN_COUNTS = {
    "cycle": 12,
    "fan_out": 15,
    "fan_in": 15,
    "gather_scatter": 10,
}

# Pattern size ranges (number of accounts involved)
PATTERN_SIZE = {
    "cycle": (3, 7),
    "fan_out": (3, 10),
    "fan_in": (3, 10),
    "gather_scatter": (5, 12),
}

# Transaction amount ranges
NORMAL_AMOUNT_RANGE = (10.0, 5000.0)
ALERT_AMOUNT_RANGE = (500.0, 50000.0)

# Account types
ACCOUNT_TYPES = ["individual", "business", "corporate"]
BANK_CODES = ["BANK_A", "BANK_B", "BANK_C", "BANK_D", "BANK_E"]
TX_TYPES = ["TRANSFER", "WIRE", "CASH", "CHECK", "ACH"]

OUTPUT_DIR = Path(__file__).parent

random.seed(SEED)

# ─── Account Generation ──────────────────────────────────────────────────────

def generate_accounts(n):
    """Generate n account records with metadata."""
    accounts = []
    for i in range(1, n + 1):
        acct_id = f"ACCT_{i:05d}"
        accounts.append({
            "account_id": acct_id,
            "account_type": random.choice(ACCOUNT_TYPES),
            "initial_balance": round(random.uniform(1000, 500000), 2),
            "bank_id": random.choice(BANK_CODES),
            "is_sar": 0,  # will be updated if account participates in a pattern
        })
    return accounts


# ─── Timestamp Helpers ────────────────────────────────────────────────────────

SIM_START = datetime(2023, 1, 1)
SIM_END = SIM_START + timedelta(days=SIM_DAYS)


def random_timestamp():
    """Return a random datetime within the simulation window."""
    delta = random.random() * (SIM_END - SIM_START).total_seconds()
    return SIM_START + timedelta(seconds=delta)


def sequential_timestamps(n, base=None, gap_hours=(1, 48)):
    """Return n timestamps in ascending order, each separated by gap_hours range."""
    ts = base or random_timestamp()
    result = [ts]
    for _ in range(n - 1):
        gap = timedelta(hours=random.uniform(*gap_hours))
        ts = ts + gap
        # Clamp to simulation window
        if ts > SIM_END:
            ts = SIM_END - timedelta(minutes=random.randint(1, 60))
        result.append(ts)
    return result


# ─── Normal Transaction Generation ───────────────────────────────────────────

def generate_normal_transactions(accounts, n, start_tx_id=1):
    """Generate n random normal (non-suspicious) transactions."""
    acct_ids = [a["account_id"] for a in accounts]
    txs = []
    for i in range(n):
        sender = random.choice(acct_ids)
        receiver = random.choice(acct_ids)
        while receiver == sender:
            receiver = random.choice(acct_ids)
        txs.append({
            "tx_id": start_tx_id + i,
            "from_id": sender,
            "to_id": receiver,
            "tx_type": random.choice(TX_TYPES),
            "amount": round(random.uniform(*NORMAL_AMOUNT_RANGE), 2),
            "timestamp": random_timestamp().strftime("%Y-%m-%d %H:%M:%S"),
            "is_sar": 0,
            "alert_id": "",
        })
    return txs


# ─── Alert Pattern Generators ────────────────────────────────────────────────

def _pick_accounts(accounts, n):
    """Randomly select n distinct account IDs."""
    pool = [a["account_id"] for a in accounts]
    return random.sample(pool, min(n, len(pool)))


def generate_cycle_pattern(accounts, alert_id, start_tx_id):
    """
    Cycle pattern: A → B → C → ... → A
    Money flows through a ring of accounts and returns to the originator.
    This is a classic layering technique in money laundering.
    """
    size = random.randint(*PATTERN_SIZE["cycle"])
    members = _pick_accounts(accounts, size)
    timestamps = sequential_timestamps(size, gap_hours=(2, 24))

    txs = []
    member_records = []
    for i in range(size):
        sender = members[i]
        receiver = members[(i + 1) % size]
        txs.append({
            "tx_id": start_tx_id + i,
            "from_id": sender,
            "to_id": receiver,
            "tx_type": random.choice(["WIRE", "TRANSFER"]),
            "amount": round(random.uniform(*ALERT_AMOUNT_RANGE), 2),
            "timestamp": timestamps[i].strftime("%Y-%m-%d %H:%M:%S"),
            "is_sar": 1,
            "alert_id": alert_id,
        })
        role = "originator" if i == 0 else ("final_receiver" if i == size - 1 else "intermediary")
        member_records.append({
            "alert_id": alert_id,
            "account_id": sender,
            "role_in_pattern": role,
        })

    pattern_record = {
        "alert_id": alert_id,
        "alert_type": "cycle",
        "num_accounts": size,
        "num_transactions": len(txs),
        "total_amount": round(sum(t["amount"] for t in txs), 2),
        "start_time": timestamps[0].strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": timestamps[-1].strftime("%Y-%m-%d %H:%M:%S"),
        "is_sar": 1,
    }
    return txs, pattern_record, member_records


def generate_fan_out_pattern(accounts, alert_id, start_tx_id):
    """
    Fan-out pattern: One account sends funds to multiple (≥2) different accounts.
    This is a common distribution/placement technique.
    """
    size = random.randint(*PATTERN_SIZE["fan_out"])
    members = _pick_accounts(accounts, size)
    hub = members[0]
    spokes = members[1:]
    timestamps = sequential_timestamps(len(spokes), gap_hours=(0.5, 12))

    txs = []
    member_records = [{"alert_id": alert_id, "account_id": hub, "role_in_pattern": "hub_sender"}]

    for i, spoke in enumerate(spokes):
        txs.append({
            "tx_id": start_tx_id + i,
            "from_id": hub,
            "to_id": spoke,
            "tx_type": random.choice(["WIRE", "TRANSFER", "ACH"]),
            "amount": round(random.uniform(*ALERT_AMOUNT_RANGE), 2),
            "timestamp": timestamps[i].strftime("%Y-%m-%d %H:%M:%S"),
            "is_sar": 1,
            "alert_id": alert_id,
        })
        member_records.append({
            "alert_id": alert_id,
            "account_id": spoke,
            "role_in_pattern": "receiver",
        })

    pattern_record = {
        "alert_id": alert_id,
        "alert_type": "fan_out",
        "num_accounts": size,
        "num_transactions": len(txs),
        "total_amount": round(sum(t["amount"] for t in txs), 2),
        "start_time": timestamps[0].strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": timestamps[-1].strftime("%Y-%m-%d %H:%M:%S"),
        "is_sar": 1,
    }
    return txs, pattern_record, member_records


def generate_fan_in_pattern(accounts, alert_id, start_tx_id):
    """
    Fan-in pattern: Multiple accounts send funds to a single account.
    This is a common collection/consolidation technique.
    """
    size = random.randint(*PATTERN_SIZE["fan_in"])
    members = _pick_accounts(accounts, size)
    hub = members[0]
    spokes = members[1:]
    timestamps = sequential_timestamps(len(spokes), gap_hours=(0.5, 12))

    txs = []
    member_records = [{"alert_id": alert_id, "account_id": hub, "role_in_pattern": "hub_receiver"}]

    for i, spoke in enumerate(spokes):
        txs.append({
            "tx_id": start_tx_id + i,
            "from_id": spoke,
            "to_id": hub,
            "tx_type": random.choice(["WIRE", "TRANSFER", "ACH"]),
            "amount": round(random.uniform(*ALERT_AMOUNT_RANGE), 2),
            "timestamp": timestamps[i].strftime("%Y-%m-%d %H:%M:%S"),
            "is_sar": 1,
            "alert_id": alert_id,
        })
        member_records.append({
            "alert_id": alert_id,
            "account_id": spoke,
            "role_in_pattern": "sender",
        })

    pattern_record = {
        "alert_id": alert_id,
        "alert_type": "fan_in",
        "num_accounts": size,
        "num_transactions": len(txs),
        "total_amount": round(sum(t["amount"] for t in txs), 2),
        "start_time": timestamps[0].strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": timestamps[-1].strftime("%Y-%m-%d %H:%M:%S"),
        "is_sar": 1,
    }
    return txs, pattern_record, member_records


def generate_gather_scatter_pattern(accounts, alert_id, start_tx_id):
    """
    Gather-scatter pattern: Funds are collected from multiple sources into a
    central account (fan-in / gather phase), then distributed out to multiple
    destinations (fan-out / scatter phase). This is a structuring-style pattern
    commonly used for layering in money laundering.
    """
    size = random.randint(*PATTERN_SIZE["gather_scatter"])
    members = _pick_accounts(accounts, size)
    hub = members[0]
    # Split remaining members into gatherers (senders) and scatterers (receivers)
    others = members[1:]
    split_point = max(1, len(others) // 2)
    gatherers = others[:split_point]
    scatterers = others[split_point:]
    if not scatterers:
        scatterers = [others[-1]]
        gatherers = others[:-1]

    # Gather phase: multiple accounts → hub
    timestamps_gather = sequential_timestamps(len(gatherers), gap_hours=(1, 8))
    # Small delay between gather and scatter
    scatter_base = timestamps_gather[-1] + timedelta(hours=random.uniform(2, 24))
    timestamps_scatter = sequential_timestamps(len(scatterers), base=scatter_base, gap_hours=(0.5, 6))

    txs = []
    member_records = [{"alert_id": alert_id, "account_id": hub, "role_in_pattern": "hub"}]
    tx_idx = 0

    # Gather phase
    for i, g in enumerate(gatherers):
        txs.append({
            "tx_id": start_tx_id + tx_idx,
            "from_id": g,
            "to_id": hub,
            "tx_type": random.choice(["WIRE", "TRANSFER"]),
            "amount": round(random.uniform(*ALERT_AMOUNT_RANGE), 2),
            "timestamp": timestamps_gather[i].strftime("%Y-%m-%d %H:%M:%S"),
            "is_sar": 1,
            "alert_id": alert_id,
        })
        member_records.append({
            "alert_id": alert_id,
            "account_id": g,
            "role_in_pattern": "gatherer",
        })
        tx_idx += 1

    # Scatter phase
    for i, s in enumerate(scatterers):
        txs.append({
            "tx_id": start_tx_id + tx_idx,
            "from_id": hub,
            "to_id": s,
            "tx_type": random.choice(["WIRE", "TRANSFER", "ACH"]),
            "amount": round(random.uniform(*ALERT_AMOUNT_RANGE), 2),
            "timestamp": timestamps_scatter[i].strftime("%Y-%m-%d %H:%M:%S"),
            "is_sar": 1,
            "alert_id": alert_id,
        })
        member_records.append({
            "alert_id": alert_id,
            "account_id": s,
            "role_in_pattern": "scatterer",
        })
        tx_idx += 1

    pattern_record = {
        "alert_id": alert_id,
        "alert_type": "gather_scatter",
        "num_accounts": size,
        "num_transactions": len(txs),
        "total_amount": round(sum(t["amount"] for t in txs), 2),
        "start_time": timestamps_gather[0].strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": timestamps_scatter[-1].strftime("%Y-%m-%d %H:%M:%S"),
        "is_sar": 1,
    }
    return txs, pattern_record, member_records


# ─── Main Execution ──────────────────────────────────────────────────────────

GENERATORS = {
    "cycle": generate_cycle_pattern,
    "fan_out": generate_fan_out_pattern,
    "fan_in": generate_fan_in_pattern,
    "gather_scatter": generate_gather_scatter_pattern,
}


def write_csv(filepath, rows, fieldnames):
    """Write a list of dicts to CSV."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows):,} rows -> {filepath.name}")


def main():
    print("=" * 70)
    print("AMLSim-Style Transaction Generator")
    print("(Custom generator implementing AMLSim's alert-pattern methodology)")
    print("=" * 70)
    print()

    # 1. Generate accounts
    print("[1/4] Generating accounts...")
    accounts = generate_accounts(NUM_ACCOUNTS)

    # 2. Generate normal (benign) transactions
    print("[2/4] Generating normal transactions...")
    all_txs = generate_normal_transactions(accounts, NUM_NORMAL_TX, start_tx_id=1)
    next_tx_id = NUM_NORMAL_TX + 1

    # 3. Generate alert patterns
    print("[3/4] Generating alert patterns...")
    all_patterns = []
    all_members = []
    alert_counter = 0
    sar_account_ids = set()

    for pattern_type, count in PATTERN_COUNTS.items():
        gen_func = GENERATORS[pattern_type]
        for _ in range(count):
            alert_counter += 1
            alert_id = f"ALERT_{alert_counter:04d}"
            txs, pattern_rec, member_recs = gen_func(accounts, alert_id, next_tx_id)
            all_txs.extend(txs)
            all_patterns.append(pattern_rec)
            all_members.extend(member_recs)
            next_tx_id += len(txs)
            # Track SAR accounts
            for m in member_recs:
                sar_account_ids.add(m["account_id"])

    # Mark SAR accounts
    for acct in accounts:
        if acct["account_id"] in sar_account_ids:
            acct["is_sar"] = 1

    # Sort transactions by timestamp for realism
    all_txs.sort(key=lambda t: t["timestamp"])
    # Re-assign tx_ids in chronological order
    for i, tx in enumerate(all_txs, 1):
        tx["tx_id"] = i

    # 4. Write output files
    print("[4/4] Writing output files...")

    write_csv(
        OUTPUT_DIR / "accounts.csv",
        accounts,
        ["account_id", "account_type", "initial_balance", "bank_id", "is_sar"],
    )

    write_csv(
        OUTPUT_DIR / "transactions.csv",
        all_txs,
        ["tx_id", "from_id", "to_id", "tx_type", "amount", "timestamp", "is_sar", "alert_id"],
    )

    write_csv(
        OUTPUT_DIR / "alert_patterns.csv",
        all_patterns,
        ["alert_id", "alert_type", "num_accounts", "num_transactions",
         "total_amount", "start_time", "end_time", "is_sar"],
    )

    write_csv(
        OUTPUT_DIR / "alert_members.csv",
        all_members,
        ["alert_id", "account_id", "role_in_pattern"],
    )

    # Summary
    print()
    print("Summary:")
    print(f"  Accounts:          {len(accounts):,}")
    print(f"  Total transactions:{len(all_txs):,}")
    print(f"  Normal txs:        {NUM_NORMAL_TX:,}")
    alert_txs = len(all_txs) - NUM_NORMAL_TX
    print(f"  Alert txs:         {alert_txs:,}")
    print(f"  Alert patterns:    {len(all_patterns):,}")
    print(f"  SAR accounts:      {len(sar_account_ids):,}")
    print()
    for ptype in PATTERN_COUNTS:
        cnt = sum(1 for p in all_patterns if p["alert_type"] == ptype)
        print(f"    {ptype:20s}: {cnt} patterns")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
