"""
generate.py — Synthetic HR/Access/Profile Data Generator for FIN04
===================================================================
Generates employee, access-event, profile-change, and relationship data
with hand-designed correlated suspicious and legitimate scenarios that
align with account IDs from the IBM AML HI-Small transaction dataset.

Usage:
    python generate.py

Prerequisites:
    - pandas, faker (pip install pandas faker)
    - ../ibm_aml/transactions_clean.csv must exist (run IBM AML inspection first)

Output files (in the same directory as this script):
    - employees.csv
    - access_events.csv
    - profile_changes.csv
    - employee_customer_map.csv
    - labeled_scenarios.csv

Random seed is fixed (SEED=42) for full reproducibility.
"""

import os
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

# ─── Configuration ────────────────────────────────────────────────────────────
SEED = 42
NUM_EMPLOYEES = 200
NUM_BACKGROUND_ACCESS_EVENTS = 800
NUM_BACKGROUND_PROFILE_CHANGES = 500
NUM_BACKGROUND_RELATIONSHIPS = 400

OUTPUT_DIR = Path(__file__).parent
IBM_AML_CLEAN = OUTPUT_DIR.parent / "ibm_aml" / "transactions_clean.csv"

random.seed(SEED)
Faker.seed(SEED)
fake = Faker()
Faker.seed(SEED)

# ─── Load Real Account IDs from IBM AML ──────────────────────────────────────

def load_real_account_ids():
    """Load account IDs from the cleaned IBM AML transaction data."""
    if not IBM_AML_CLEAN.exists():
        print(f"ERROR: {IBM_AML_CLEAN} not found.")
        print("Please run the IBM AML inspection/cleaning step first.")
        sys.exit(1)

    df = pd.read_csv(IBM_AML_CLEAN, low_memory=False)
    # Collect unique account IDs from both sender and receiver columns
    # Column names depend on the cleaned schema — try common variants
    id_cols = []
    for col_name in ["from_id", "to_id", "from_account", "to_account",
                     "sender_id", "receiver_id", "account", "Account"]:
        if col_name in df.columns:
            id_cols.append(col_name)

    if not id_cols:
        print(f"ERROR: Could not find account ID columns in {IBM_AML_CLEAN}")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    all_ids = set()
    for col in id_cols:
        all_ids.update(df[col].dropna().astype(str).unique())

    print(f"  Loaded {len(all_ids):,} unique account IDs from IBM AML data")
    return sorted(all_ids)


# ─── Employee Generation ─────────────────────────────────────────────────────

ROLES = [
    "Relationship Manager", "Account Manager", "Compliance Officer",
    "KYC Analyst", "Operations Specialist", "Branch Manager",
    "Risk Analyst", "Fraud Investigator", "Teller", "Senior Advisor",
    "Compliance Director", "IT Security Analyst", "Treasury Analyst",
    "Audit Associate", "Customer Service Rep",
]

DEPARTMENTS = [
    "Retail Banking", "Corporate Banking", "Compliance", "Risk Management",
    "Operations", "Wealth Management", "Treasury", "IT Security", "Audit",
    "Customer Service",
]

ACCESS_LEVELS = ["L1", "L2", "L3", "L4", "L5"]  # L1=lowest, L5=admin


def generate_employees(n):
    """Generate n employee records."""
    employees = []
    for i in range(1, n + 1):
        emp_id = f"EMP_{i:04d}"
        employees.append({
            "employee_id": emp_id,
            "name": fake.name(),
            "role": random.choice(ROLES),
            "department": random.choice(DEPARTMENTS),
            "hire_date": fake.date_between(
                start_date=datetime(2015, 1, 1),
                end_date=datetime(2023, 6, 1),
            ).isoformat(),
            "access_level": random.choice(ACCESS_LEVELS),
        })
    return employees


# ─── Background Data Generation ──────────────────────────────────────────────

ACTIONS = ["grant", "revoke", "modify"]
FIELDS_CHANGED = [
    "address", "phone", "email", "name", "tax_id", "beneficial_owner",
    "risk_rating", "account_type", "spending_limit", "wire_transfer_limit",
]
RELATIONSHIP_TYPES = ["account_manager", "approver", "reviewer"]


def random_dt(start=datetime(2022, 9, 1), end=datetime(2022, 9, 18)):
    """Return a random datetime between start and end."""
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=random.random() * delta)


def generate_background_access_events(employees, account_ids, n, start_id=1):
    """Generate background (non-scenario) access events."""
    events = []
    emp_ids = [e["employee_id"] for e in employees]
    for i in range(n):
        action = random.choice(ACTIONS)
        old_val, new_val = "", ""
        if action == "modify":
            old_val = str(random.randint(1000, 50000))
            new_val = str(random.randint(1000, 50000))
        elif action == "grant":
            new_val = random.choice(["wire_transfer", "batch_payment", "forex",
                                     "large_transaction", "api_access", "admin"])
        elif action == "revoke":
            old_val = random.choice(["wire_transfer", "batch_payment", "forex",
                                     "large_transaction", "api_access", "admin"])
        events.append({
            "event_id": f"EVT_{start_id + i:06d}",
            "employee_id": random.choice(emp_ids),
            "action": action,
            "target_account_id": random.choice(account_ids),
            "old_value": old_val,
            "new_value": new_val,
            "timestamp": random_dt().strftime("%Y-%m-%d %H:%M:%S"),
            "scenario_type": "",
            "scenario_id": "",
        })
    return events


def generate_background_profile_changes(employees, account_ids, n, start_id=1):
    """Generate background (non-scenario) profile changes."""
    changes = []
    emp_ids = [e["employee_id"] for e in employees]
    for i in range(n):
        field = random.choice(FIELDS_CHANGED)
        old_val = fake.word()
        new_val = fake.word()
        if field == "address":
            old_val = fake.address().replace("\n", ", ")
            new_val = fake.address().replace("\n", ", ")
        elif field == "phone":
            old_val = fake.phone_number()
            new_val = fake.phone_number()
        elif field == "email":
            old_val = fake.email()
            new_val = fake.email()
        elif field in ("spending_limit", "wire_transfer_limit"):
            old_val = str(random.randint(1000, 50000))
            new_val = str(random.randint(1000, 50000))
        elif field == "risk_rating":
            old_val = random.choice(["low", "medium", "high"])
            new_val = random.choice(["low", "medium", "high"])
        changes.append({
            "change_id": f"CHG_{start_id + i:06d}",
            "customer_id": random.choice(account_ids),
            "field_changed": field,
            "old_value": old_val,
            "new_value": new_val,
            "changed_by_employee_id": random.choice(emp_ids),
            "timestamp": random_dt().strftime("%Y-%m-%d %H:%M:%S"),
        })
    return changes


def generate_background_relationships(employees, account_ids, n):
    """Generate background employee-customer relationship mappings."""
    emp_ids = [e["employee_id"] for e in employees]
    rels = []
    seen = set()
    for _ in range(n):
        emp = random.choice(emp_ids)
        cust = random.choice(account_ids)
        key = (emp, cust)
        if key in seen:
            continue
        seen.add(key)
        rels.append({
            "employee_id": emp,
            "customer_id": cust,
            "relationship_type": random.choice(RELATIONSHIP_TYPES),
        })
    return rels


# ═══════════════════════════════════════════════════════════════════════════════
# HAND-DESIGNED CORRELATED SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════
#
# Each scenario consists of:
#   1. An access_event (employee action on an account)
#   2. Correlated profile_change(s)
#   3. A labeled_scenario record with human-readable description
#
# Suspicious scenarios: employee action precedes anomalous activity on the
# same account within a short time window (typically 1-48 hours).
#
# Legitimate look-alike scenarios: superficially similar pattern but with
# an innocent business explanation.
# ═══════════════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO TIMING & TRANSACTION CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# IBM AML data window
_IBM_START = datetime(2022, 9, 1)
_IBM_END = datetime(2022, 9, 18)

# Per-scenario: (min_gap_hours, max_gap_hours) between access event and
# first injected transaction. Derived from each scenario's description.
SCENARIO_TIMING = {
    "S01": (1, 48),    # "within 48 hours"
    "S02": (1, 6),     # "within 6 hours"
    "S03": (1, 24),    # "within 24h"
    "S04": (1, 36),    # "within 36 hours"
    "S05": (1, 48),    # "within 48h"
    "S06": (1, 12),    # "within 12 hours"
    "S07": (1, 48),    # "within 48 hours"
    "S08": (0.5, 2),   # "immediately"
    "S09": (1, 24),    # "within 24h"
    "S10": (0.5, 2),   # "immediately"
    "S11": (1, 4),     # "within 4 hours"
    "S12": (1, 12),    # "within 12h"
    "S13": (0.5, 2),   # "within 2 hours"
    "S14": (1, 36),    # "within 36h"
    "S15": (0.5, 2),   # "immediately"
    "S16": (1, 6),     # "within 6 hours"
    "S17": (0.5, 1),   # "immediately"
    "S18": (1, 48),    # "within 48h"
    # Legitimate: flexible timing, just inside the window
    "L01": (1, 24), "L02": (1, 48), "L03": (1, 12), "L04": (1, 48),
    "L05": (1, 48), "L06": (1, 48), "L07": (1, 48), "L08": (1, 24),
    "L09": (1, 48), "L10": (1, 48), "L11": (1, 48), "L12": (1, 24),
    "L13": (1, 48), "L14": (1, 24), "L15": (1, 48), "L16": (1, 48),
    "L17": (1, 48), "L18": (1, 48),
}


def _compute_base_time(scenario_id):
    """Compute access event timestamp for a scenario.

    access_event_time = uniform random within
        [IBM_START, IBM_END - max_gap_hours]

    This guarantees both the access event and its injected transactions
    stay strictly inside the 2022-09-01 to 2022-09-18 window.
    """
    min_gap_h, max_gap_h = SCENARIO_TIMING[scenario_id]
    # Ensure the latest possible access time leaves room for max_gap
    latest_access = _IBM_END - timedelta(hours=max_gap_h)
    delta_secs = (latest_access - _IBM_START).total_seconds()
    offset = random.random() * delta_secs
    return _IBM_START + timedelta(seconds=offset)


# Per-scenario transaction generation config.
# Only scenarios with has_transactional_consequence=True are included.
# Keys: count, amount_range, currency, payment_format, is_laundering
SCENARIO_TXN_CONFIG = {
    # ── Suspicious ────────────────────────────────────────────────────────
    "S01": {  # 12 split transfers of $9,500 each
        "count": 12, "amount_range": (9200, 9500),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S02": {  # $450K wire to offshore
        "count": 1, "amount_range": (445000, 455000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S03": {  # 20+ rapid transactions totaling $800K
        "count": 20, "amount_range": (35000, 45000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S04": {  # 24 transactions between $6K-$45K
        "count": 24, "amount_range": (6000, 45000),
        "currency": "US Dollar", "payment_format": "ACH", "is_laundering": 1,
    },
    "S05": {  # layered transfers through 3 accounts totaling $1.2M
        "count": 3, "amount_range": (380000, 420000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S06": {  # $350K in rapid transfers within 12 hours
        "count": 5, "amount_range": (65000, 75000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S07": {  # multiple cash deposits ($9,900 each)
        "count": 8, "amount_range": (9800, 9900),
        "currency": "US Dollar", "payment_format": "Cash", "is_laundering": 1,
    },
    "S08": {  # wire transfers ($75K+ each) to multiple countries
        "count": 4, "amount_range": (75000, 120000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S09": {  # 50+ payments of $2,000-$4,999 each (smurfing)
        "count": 50, "amount_range": (2000, 4999),
        "currency": "US Dollar", "payment_format": "ACH", "is_laundering": 1,
    },
    "S10": {  # large money order purchases ($9,800 each)
        "count": 8, "amount_range": (9700, 9800),
        "currency": "US Dollar", "payment_format": "Cheque", "is_laundering": 1,
    },
    "S11": {  # single $2.5M wire transfer
        "count": 1, "amount_range": (2450000, 2550000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S12": {  # forex conversions USD->EUR->CHF->GBP totaling $600K
        "count": 4, "amount_range": (140000, 160000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
        "receiving_currencies": ["Euro", "Swiss Franc", "UK Pound", "US Dollar"],
    },
    "S13": {  # $200K to each of 2 offshore payees
        "count": 2, "amount_range": (195000, 205000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S14": {  # burst of high-value purchases
        "count": 6, "amount_range": (25000, 40000),
        "currency": "US Dollar", "payment_format": "Credit Card", "is_laundering": 1,
    },
    "S15": {  # $500K in wire transfers to sanctioned jurisdictions
        "count": 3, "amount_range": (160000, 175000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S16": {  # coordinated transfers from 3 accounts to same dest
        "count": 3, "amount_range": (80000, 120000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    "S17": {  # automated bot-like transactions (100+ per hour)
        "count": 20, "amount_range": (1000, 5000),
        "currency": "US Dollar", "payment_format": "ACH", "is_laundering": 1,
    },
    "S18": {  # $1.8M in high-value transactions
        "count": 6, "amount_range": (280000, 320000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 1,
    },
    # ── Legitimate (only those with transactional consequence) ────────────
    "L01": {  # payroll bonus + tax splits
        "count": 5, "amount_range": (8000, 30000),
        "currency": "US Dollar", "payment_format": "ACH", "is_laundering": 0,
    },
    "L02": {  # single large purchase (vehicle)
        "count": 1, "amount_range": (35000, 45000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 0,
    },
    "L03": {  # treasury sweep between subsidiaries
        "count": 4, "amount_range": (50000, 200000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 0,
    },
    "L07": {  # holiday spending increase
        "count": 3, "amount_range": (5000, 15000),
        "currency": "US Dollar", "payment_format": "Credit Card", "is_laundering": 0,
    },
    "L08": {  # batch vendor payments
        "count": 5, "amount_range": (2000, 8000),
        "currency": "US Dollar", "payment_format": "ACH", "is_laundering": 0,
    },
    "L10": {  # forex trade finance
        "count": 2, "amount_range": (20000, 60000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 0,
        "receiving_currencies": ["Euro", "Japanese Yen"],
    },
    "L11": {  # sole proprietor normal transactions
        "count": 3, "amount_range": (5000, 20000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 0,
    },
    "L13": {  # charitable donation wire
        "count": 1, "amount_range": (290000, 310000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 0,
    },
    "L14": {  # vendor payments
        "count": 3, "amount_range": (10000, 40000),
        "currency": "US Dollar", "payment_format": "ACH", "is_laundering": 0,
    },
    "L15": {  # real estate escrow payment
        "count": 1, "amount_range": (840000, 860000),
        "currency": "US Dollar", "payment_format": "Wire", "is_laundering": 0,
    },
    "L17": {  # API accounting scheduled payments
        "count": 3, "amount_range": (1000, 5000),
        "currency": "US Dollar", "payment_format": "ACH", "is_laundering": 0,
    },
}


def generate_correlated_scenarios(employees, account_ids):
    """
    Generate ~36 hand-designed scenarios (18 suspicious + 18 legitimate).
    Returns (access_events, profile_changes, labeled_scenarios, relationships).
    """

    # Select dedicated accounts and employees for scenarios
    # Use deterministic slices of the real account IDs
    scenario_accounts = account_ids[100:180]  # 80 real account IDs for scenarios
    scenario_employees = employees[10:50]  # 40 employees for scenarios

    access_events = []
    profile_changes = []
    labeled_scenarios = []
    relationships = []

    evt_counter = 90000  # High IDs to avoid collision with background data
    chg_counter = 90000

    def next_evt_id():
        nonlocal evt_counter
        evt_counter += 1
        return f"EVT_{evt_counter:06d}"

    def next_chg_id():
        nonlocal chg_counter
        chg_counter += 1
        return f"CHG_{chg_counter:06d}"

    # ───────────────────────────────────────────────────────────────────────
    # SUSPICIOUS SCENARIOS (S01-S18)
    # ───────────────────────────────────────────────────────────────────────

    # S01: Employee raises transfer limit -> split transfers within 48h
    # Classic structuring: limit increase enables splitting a large amount
    # into many sub-threshold transactions
    s_acct = scenario_accounts[0]
    s_emp = scenario_employees[0]["employee_id"]
    base_time = _compute_base_time("S01")
    evt_id_1 = next_evt_id()
    access_events.append({
        "event_id": evt_id_1,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "transfer_limit=10000",
        "new_value": "transfer_limit=100000",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S01",
    })
    chg_id_1 = next_chg_id()
    profile_changes.append({
        "change_id": chg_id_1,
        "customer_id": s_acct,
        "field_changed": "spending_limit",
        "old_value": "10000",
        "new_value": "100000",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S01",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee raises transfer limit from $10K to $100K. "
                       "Within 48 hours, account performs 12 split transfers of "
                       "$9,500 each (just below reporting threshold). Classic structuring.",
        "related_event_ids": evt_id_1,
        "related_transaction_ids": "",  # Would link to IBM AML tx_ids downstream
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S02: Employee grants wire-transfer access -> immediate large offshore wire
    s_acct = scenario_accounts[1]
    s_emp = scenario_employees[1]["employee_id"]
    base_time = _compute_base_time("S02")
    evt_id_2 = next_evt_id()
    access_events.append({
        "event_id": evt_id_2,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "wire_transfer",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S02",
    })
    chg_id_2 = next_chg_id()
    profile_changes.append({
        "change_id": chg_id_2,
        "customer_id": s_acct,
        "field_changed": "wire_transfer_limit",
        "old_value": "0",
        "new_value": "500000",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S02",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee grants wire-transfer access to individual account "
                       "that never had it. Within 6 hours, a $450K wire is sent to "
                       "an offshore jurisdiction. No prior wire history.",
        "related_event_ids": evt_id_2,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S03: Employee modifies KYC verification -> rapid activity spike
    s_acct = scenario_accounts[2]
    s_emp = scenario_employees[2]["employee_id"]
    base_time = _compute_base_time("S03")
    evt_id_3 = next_evt_id()
    access_events.append({
        "event_id": evt_id_3,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "kyc_status=pending",
        "new_value": "kyc_status=verified",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S03",
    })
    chg_id_3 = next_chg_id()
    profile_changes.append({
        "change_id": chg_id_3,
        "customer_id": s_acct,
        "field_changed": "risk_rating",
        "old_value": "high",
        "new_value": "low",
        "changed_by_employee_id": s_emp,
        "timestamp": (base_time + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "reviewer"})
    labeled_scenarios.append({
        "scenario_id": "S03",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee bypasses KYC verification (pending->verified) and "
                       "downgrades risk rating (high->low) on same account. Within 24h, "
                       "account executes 20+ rapid transactions totaling $800K.",
        "related_event_ids": f"{evt_id_3}",
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S04: Employee lowers monitoring threshold -> sudden high-value txns
    s_acct = scenario_accounts[3]
    s_emp = scenario_employees[3]["employee_id"]
    base_time = _compute_base_time("S04")
    evt_id_4 = next_evt_id()
    access_events.append({
        "event_id": evt_id_4,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "monitoring_threshold=5000",
        "new_value": "monitoring_threshold=50000",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S04",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S04",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee raises monitoring threshold from $5K to $50K, "
                       "effectively hiding mid-size transactions from alerts. "
                       "24 transactions between $6K-$45K follow within 36 hours.",
        "related_event_ids": evt_id_4,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S05: Employee changes beneficial ownership -> layered transfers
    s_acct = scenario_accounts[4]
    s_emp = scenario_employees[4]["employee_id"]
    base_time = _compute_base_time("S05")
    evt_id_5 = next_evt_id()
    access_events.append({
        "event_id": evt_id_5,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "beneficial_owner=John Smith",
        "new_value": "beneficial_owner=Shell Corp LLC",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S05",
    })
    chg_id_5 = next_chg_id()
    profile_changes.append({
        "change_id": chg_id_5,
        "customer_id": s_acct,
        "field_changed": "beneficial_owner",
        "old_value": "John Smith",
        "new_value": "Shell Corp LLC",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S05",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee changes beneficial ownership from individual to "
                       "opaque shell company. Within 48h, layered transfers through "
                       "3 intermediate accounts totaling $1.2M.",
        "related_event_ids": evt_id_5,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S06: New employee accesses dormant account -> rapid fund flow
    s_acct = scenario_accounts[5]
    s_emp = scenario_employees[5]["employee_id"]
    base_time = _compute_base_time("S06")
    evt_id_6 = next_evt_id()
    access_events.append({
        "event_id": evt_id_6,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "full_access",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S06",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S06",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Recently-hired employee (< 60 days tenure) grants themselves "
                       "full access to a dormant account. Account reactivated with "
                       "$350K in rapid transfers within 12 hours.",
        "related_event_ids": evt_id_6,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S07: Employee modifies address to PO Box -> cash deposits follow
    s_acct = scenario_accounts[6]
    s_emp = scenario_employees[6]["employee_id"]
    base_time = _compute_base_time("S07")
    evt_id_7 = next_evt_id()
    chg_id_7 = next_chg_id()
    access_events.append({
        "event_id": evt_id_7,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "address=123 Main St, Springfield",
        "new_value": "address=PO Box 9999, Offshore City",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S07",
    })
    profile_changes.append({
        "change_id": chg_id_7,
        "customer_id": s_acct,
        "field_changed": "address",
        "old_value": "123 Main St, Springfield",
        "new_value": "PO Box 9999, Offshore City",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S07",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee changes customer address from residential to "
                       "suspicious PO Box in offshore jurisdiction. Followed by "
                       "multiple cash deposits ($9,900 each) within 48 hours.",
        "related_event_ids": evt_id_7,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S08: Employee overrides fraud alert -> subsequent suspicious activity
    s_acct = scenario_accounts[7]
    s_emp = scenario_employees[7]["employee_id"]
    base_time = _compute_base_time("S08")
    evt_id_8 = next_evt_id()
    access_events.append({
        "event_id": evt_id_8,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "fraud_alert=active",
        "new_value": "fraud_alert=dismissed",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S08",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "reviewer"})
    labeled_scenarios.append({
        "scenario_id": "S08",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee dismisses active fraud alert on account without "
                       "documented justification. Account immediately resumes "
                       "suspicious wire transfers ($75K+ each) to multiple countries.",
        "related_event_ids": evt_id_8,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S09: Employee grants batch-payment access -> many small payments
    s_acct = scenario_accounts[8]
    s_emp = scenario_employees[8]["employee_id"]
    base_time = _compute_base_time("S09")
    evt_id_9 = next_evt_id()
    access_events.append({
        "event_id": evt_id_9,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "batch_payment",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S09",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "approver"})
    labeled_scenarios.append({
        "scenario_id": "S09",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee grants batch-payment capability to personal account. "
                       "Within 24h, 50+ payments of $2,000-$4,999 each are sent to "
                       "different recipients (smurfing/structuring pattern).",
        "related_event_ids": evt_id_9,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S10: Employee changes account type -> money orders follow
    s_acct = scenario_accounts[9]
    s_emp = scenario_employees[9]["employee_id"]
    base_time = _compute_base_time("S10")
    evt_id_10 = next_evt_id()
    chg_id_10 = next_chg_id()
    access_events.append({
        "event_id": evt_id_10,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "account_type=personal",
        "new_value": "account_type=business",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S10",
    })
    profile_changes.append({
        "change_id": chg_id_10,
        "customer_id": s_acct,
        "field_changed": "account_type",
        "old_value": "personal",
        "new_value": "business",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S10",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee converts personal account to business without "
                       "proper documentation. Account immediately used for large "
                       "money order purchases ($9,800 each, just under $10K threshold).",
        "related_event_ids": evt_id_10,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S11: Employee removes dual-authorization -> large single transfer out
    s_acct = scenario_accounts[10]
    s_emp = scenario_employees[10]["employee_id"]
    base_time = _compute_base_time("S11")
    evt_id_11 = next_evt_id()
    access_events.append({
        "event_id": evt_id_11,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "dual_auth=required",
        "new_value": "dual_auth=disabled",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S11",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "approver"})
    labeled_scenarios.append({
        "scenario_id": "S11",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee disables dual-authorization requirement on "
                       "corporate account. Within 4 hours, a single $2.5M wire "
                       "transfer is executed without secondary approval.",
        "related_event_ids": evt_id_11,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S12: Employee modifies currency settings -> rapid forex transactions
    s_acct = scenario_accounts[11]
    s_emp = scenario_employees[11]["employee_id"]
    base_time = _compute_base_time("S12")
    evt_id_12 = next_evt_id()
    access_events.append({
        "event_id": evt_id_12,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "forex",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S12",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S12",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee enables multi-currency/forex on account with no "
                       "international business justification. Within 12h, rapid forex "
                       "conversions USD->EUR->CHF->GBP totaling $600K (layering).",
        "related_event_ids": evt_id_12,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S13: Employee adds new payee -> immediate fund transfers
    s_acct = scenario_accounts[12]
    s_emp = scenario_employees[12]["employee_id"]
    base_time = _compute_base_time("S13")
    evt_id_13 = next_evt_id()
    access_events.append({
        "event_id": evt_id_13,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "payees=[]",
        "new_value": "payees=[OFFSHORE_ENTITY_A, OFFSHORE_ENTITY_B]",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S13",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S13",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee adds two offshore entities as payees without customer "
                       "request documentation. Immediate transfers of $200K to each "
                       "payee within 2 hours.",
        "related_event_ids": evt_id_13,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S14: Employee escalates spending limit -> burst purchases then cash-back
    s_acct = scenario_accounts[13]
    s_emp = scenario_employees[13]["employee_id"]
    base_time = _compute_base_time("S14")
    evt_id_14 = next_evt_id()
    chg_id_14 = next_chg_id()
    access_events.append({
        "event_id": evt_id_14,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "spending_limit=5000",
        "new_value": "spending_limit=200000",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S14",
    })
    profile_changes.append({
        "change_id": chg_id_14,
        "customer_id": s_acct,
        "field_changed": "spending_limit",
        "old_value": "5000",
        "new_value": "200000",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "S14",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee increases spending limit 40x (from $5K to $200K). "
                       "Within 36h, burst of high-value purchases followed by "
                       "cash-back refund requests (purchase-return laundering scheme).",
        "related_event_ids": evt_id_14,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S15: Employee modifies AML screening exclusion -> sanctioned region txns
    s_acct = scenario_accounts[14]
    s_emp = scenario_employees[14]["employee_id"]
    base_time = _compute_base_time("S15")
    evt_id_15 = next_evt_id()
    access_events.append({
        "event_id": evt_id_15,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "aml_screening=enabled",
        "new_value": "aml_screening=excluded",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S15",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "reviewer"})
    labeled_scenarios.append({
        "scenario_id": "S15",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee excludes account from AML screening pipeline. "
                       "Account immediately sends $500K in wire transfers to "
                       "sanctioned jurisdictions that would have been flagged.",
        "related_event_ids": evt_id_15,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S16: Employee bulk-modifies customer profiles -> coordinated transfers
    s_acct_16a = scenario_accounts[15]
    s_acct_16b = scenario_accounts[16]
    s_acct_16c = scenario_accounts[17]
    s_emp = scenario_employees[15]["employee_id"]
    base_time = _compute_base_time("S16")
    evt_id_16a = next_evt_id()
    evt_id_16b = next_evt_id()
    evt_id_16c = next_evt_id()
    for acct in [s_acct_16a, s_acct_16b, s_acct_16c]:
        access_events.append({
            "event_id": evt_id_16a if acct == s_acct_16a else (evt_id_16b if acct == s_acct_16b else evt_id_16c),
            "employee_id": s_emp,
            "action": "modify",
            "target_account_id": acct,
            "old_value": "risk_rating=high",
            "new_value": "risk_rating=low",
            "timestamp": (base_time + timedelta(minutes=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S"),
            "scenario_type": "suspicious",
            "scenario_id": "S16",
        })
        profile_changes.append({
            "change_id": next_chg_id(),
            "customer_id": acct,
            "field_changed": "risk_rating",
            "old_value": "high",
            "new_value": "low",
            "changed_by_employee_id": s_emp,
            "timestamp": (base_time + timedelta(minutes=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S"),
        })
        relationships.append({"employee_id": s_emp, "customer_id": acct,
                              "relationship_type": "reviewer"})
    labeled_scenarios.append({
        "scenario_id": "S16",
        "scenario_type": "suspicious",
        "account_id": f"{s_acct_16a};{s_acct_16b};{s_acct_16c}",
        "employee_id": s_emp,
        "description": "Employee bulk-downgrades risk rating on 3 related accounts "
                       "within 30 minutes. All three accounts then execute coordinated "
                       "transfers to the same destination within 6 hours.",
        "related_event_ids": f"{evt_id_16a};{evt_id_16b};{evt_id_16c}",
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S17: Employee grants API access -> automated rapid transactions
    s_acct = scenario_accounts[18]
    s_emp = scenario_employees[16]["employee_id"]
    base_time = _compute_base_time("S17")
    evt_id_17 = next_evt_id()
    access_events.append({
        "event_id": evt_id_17,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "api_access",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S17",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "approver"})
    labeled_scenarios.append({
        "scenario_id": "S17",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee grants API access to personal account without "
                       "business justification. Automated bot-like transactions "
                       "(100+ per hour) begin immediately, spreading funds across "
                       "dozens of accounts.",
        "related_event_ids": evt_id_17,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # S18: Employee changes risk rating downward -> high-value txns follow
    s_acct = scenario_accounts[19]
    s_emp = scenario_employees[17]["employee_id"]
    base_time = _compute_base_time("S18")
    evt_id_18 = next_evt_id()
    chg_id_18 = next_chg_id()
    access_events.append({
        "event_id": evt_id_18,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "risk_rating=high",
        "new_value": "risk_rating=low",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "suspicious",
        "scenario_id": "S18",
    })
    profile_changes.append({
        "change_id": chg_id_18,
        "customer_id": s_acct,
        "field_changed": "risk_rating",
        "old_value": "high",
        "new_value": "low",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "reviewer"})
    labeled_scenarios.append({
        "scenario_id": "S18",
        "scenario_type": "suspicious",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Employee manually overrides risk model, downgrading account "
                       "from high to low risk. Within 48h, $1.8M in high-value "
                       "transactions bypass enhanced monitoring that would have applied.",
        "related_event_ids": evt_id_18,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # ───────────────────────────────────────────────────────────────────────
    # LEGITIMATE LOOK-ALIKE SCENARIOS (L01-L18)
    # ───────────────────────────────────────────────────────────────────────

    # L01: Payroll bonus processing — authorized limit increase + tax splits
    s_acct = scenario_accounts[20]
    s_emp = scenario_employees[18]["employee_id"]
    base_time = _compute_base_time("L01")
    evt_id_l01 = next_evt_id()
    chg_id_l01 = next_chg_id()
    access_events.append({
        "event_id": evt_id_l01,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "transfer_limit=25000",
        "new_value": "transfer_limit=150000",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L01",
    })
    profile_changes.append({
        "change_id": chg_id_l01,
        "customer_id": s_acct,
        "field_changed": "spending_limit",
        "old_value": "25000",
        "new_value": "150000",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L01",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Authorized payroll limit increase for end-of-quarter bonus "
                       "distribution. Multiple payments are tax withholding splits "
                       "(federal, state, FICA). Approved by branch manager, documented.",
        "related_event_ids": evt_id_l01,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L02: Annual account review — verified large-purchase limit adjustment
    s_acct = scenario_accounts[21]
    s_emp = scenario_employees[19]["employee_id"]
    base_time = _compute_base_time("L02")
    evt_id_l02 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l02,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "spending_limit=20000",
        "new_value": "spending_limit=75000",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L02",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L02",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Annual account review: customer's income verification shows "
                       "salary increase, limit adjusted accordingly. Single large "
                       "purchase (new vehicle) follows. Fully documented with "
                       "income verification on file.",
        "related_event_ids": evt_id_l02,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L03: Corporate treasury sweep — authorized batch transfers
    s_acct = scenario_accounts[22]
    s_emp = scenario_employees[20]["employee_id"]
    base_time = _compute_base_time("L03")
    evt_id_l03 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l03,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "batch_payment",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L03",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "approver"})
    labeled_scenarios.append({
        "scenario_id": "L03",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Month-end treasury sweep: corporate customer moves funds "
                       "between subsidiaries as part of routine cash management. "
                       "All recipient accounts belong to the same corporate group. "
                       "Pre-authorized standing order.",
        "related_event_ids": evt_id_l03,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L04: Employee onboarding access grants — standard new-hire provisioning
    s_acct = scenario_accounts[23]
    s_emp = scenario_employees[21]["employee_id"]
    base_time = _compute_base_time("L04")
    evt_id_l04 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l04,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "view_only",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L04",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "reviewer"})
    labeled_scenarios.append({
        "scenario_id": "L04",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Standard onboarding: new hire receives view-only access to "
                       "assigned customer accounts. Approved by IT Security and line "
                       "manager via standard ticketing system. No transactional access.",
        "related_event_ids": evt_id_l04,
        "related_transaction_ids": "",
        "has_transactional_consequence": False,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L05: KYC renewal — routine re-verification + profile update
    s_acct = scenario_accounts[24]
    s_emp = scenario_employees[22]["employee_id"]
    base_time = _compute_base_time("L05")
    evt_id_l05 = next_evt_id()
    chg_id_l05 = next_chg_id()
    access_events.append({
        "event_id": evt_id_l05,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "kyc_status=expired",
        "new_value": "kyc_status=verified",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L05",
    })
    profile_changes.append({
        "change_id": chg_id_l05,
        "customer_id": s_acct,
        "field_changed": "risk_rating",
        "old_value": "medium",
        "new_value": "low",
        "changed_by_employee_id": s_emp,
        "timestamp": (base_time + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "reviewer"})
    labeled_scenarios.append({
        "scenario_id": "L05",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Scheduled KYC renewal: expired verification refreshed with "
                       "new documentation (passport, utility bill). Risk downgrade "
                       "from medium to low based on 5-year clean history. Compliance "
                       "officer co-signed.",
        "related_event_ids": evt_id_l05,
        "related_transaction_ids": "",
        "has_transactional_consequence": False,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L06: Verified customer relocation — address change
    s_acct = scenario_accounts[25]
    s_emp = scenario_employees[23]["employee_id"]
    base_time = _compute_base_time("L06")
    evt_id_l06 = next_evt_id()
    chg_id_l06 = next_chg_id()
    access_events.append({
        "event_id": evt_id_l06,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "address=456 Oak Ave, Portland",
        "new_value": "address=789 Pine St, Seattle",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L06",
    })
    profile_changes.append({
        "change_id": chg_id_l06,
        "customer_id": s_acct,
        "field_changed": "address",
        "old_value": "456 Oak Ave, Portland",
        "new_value": "789 Pine St, Seattle",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L06",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Customer relocates between domestic cities. Address updated "
                       "with verified documentation (new lease agreement). No change "
                       "in transaction patterns. Customer-initiated via branch visit.",
        "related_event_ids": evt_id_l06,
        "related_transaction_ids": "",
        "has_transactional_consequence": False,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L07: Seasonal limit adjustment — holiday spending increase
    s_acct = scenario_accounts[26]
    s_emp = scenario_employees[24]["employee_id"]
    base_time = _compute_base_time("L07")
    evt_id_l07 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l07,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "spending_limit=10000",
        "new_value": "spending_limit=30000",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L07",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L07",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Customer requests temporary holiday spending limit increase "
                       "via phone (recorded). Standard seasonal adjustment matching "
                       "prior year pattern. Auto-reverts after 45 days.",
        "related_event_ids": evt_id_l07,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L08: Authorized vendor payments — batch payment setup for known vendors
    s_acct = scenario_accounts[27]
    s_emp = scenario_employees[25]["employee_id"]
    base_time = _compute_base_time("L08")
    evt_id_l08 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l08,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "batch_payment",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L08",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "approver"})
    labeled_scenarios.append({
        "scenario_id": "L08",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Small business customer sets up batch payments for known, "
                       "verified vendors (suppliers, utilities, rent). All payees "
                       "pre-verified and documented. Consistent with business type.",
        "related_event_ids": evt_id_l08,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L09: Account migration — type change during system upgrade
    s_acct = scenario_accounts[28]
    s_emp = scenario_employees[26]["employee_id"]
    base_time = _compute_base_time("L09")
    evt_id_l09 = next_evt_id()
    chg_id_l09 = next_chg_id()
    access_events.append({
        "event_id": evt_id_l09,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "account_type=savings_legacy",
        "new_value": "account_type=savings_v2",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L09",
    })
    profile_changes.append({
        "change_id": chg_id_l09,
        "customer_id": s_acct,
        "field_changed": "account_type",
        "old_value": "savings_legacy",
        "new_value": "savings_v2",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L09",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Scheduled system migration: legacy savings accounts batch-"
                       "converted to new platform format. Performed during maintenance "
                       "window. No changes to account capabilities or transaction behavior.",
        "related_event_ids": evt_id_l09,
        "related_transaction_ids": "",
        "has_transactional_consequence": False,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L10: Currency setup — new international customer with verified forex needs
    s_acct = scenario_accounts[29]
    s_emp = scenario_employees[27]["employee_id"]
    base_time = _compute_base_time("L10")
    evt_id_l10 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l10,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "forex",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L10",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L10",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Import/export business customer opens multi-currency account. "
                       "Forex access enabled with documented trade finance needs "
                       "(letters of credit, import invoices). Compliance pre-approved.",
        "related_event_ids": evt_id_l10,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L11: Dual-auth removal — small business single-signatory
    s_acct = scenario_accounts[30]
    s_emp = scenario_employees[28]["employee_id"]
    base_time = _compute_base_time("L11")
    evt_id_l11 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l11,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "dual_auth=required",
        "new_value": "dual_auth=disabled",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L11",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "approver"})
    labeled_scenarios.append({
        "scenario_id": "L11",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Sole proprietor requests removal of dual-authorization "
                       "(previously set when they had a business partner who left). "
                       "Board resolution and legal docs on file. Transaction amounts "
                       "remain consistent with historical pattern.",
        "related_event_ids": evt_id_l11,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L12: Compliance-driven batch profile update — regulatory requirement
    s_acct_l12a = scenario_accounts[31]
    s_acct_l12b = scenario_accounts[32]
    s_emp = scenario_employees[29]["employee_id"]
    base_time = _compute_base_time("L12")
    evt_id_l12a = next_evt_id()
    evt_id_l12b = next_evt_id()
    for acct, eid in [(s_acct_l12a, evt_id_l12a), (s_acct_l12b, evt_id_l12b)]:
        access_events.append({
            "event_id": eid,
            "employee_id": s_emp,
            "action": "modify",
            "target_account_id": acct,
            "old_value": "tax_classification=unverified",
            "new_value": "tax_classification=verified_W9",
            "timestamp": (base_time + timedelta(minutes=random.randint(1, 60))).strftime("%Y-%m-%d %H:%M:%S"),
            "scenario_type": "legitimate",
            "scenario_id": "L12",
        })
        profile_changes.append({
            "change_id": next_chg_id(),
            "customer_id": acct,
            "field_changed": "tax_id",
            "old_value": "pending",
            "new_value": "verified",
            "changed_by_employee_id": s_emp,
            "timestamp": (base_time + timedelta(minutes=random.randint(1, 60))).strftime("%Y-%m-%d %H:%M:%S"),
        })
        relationships.append({"employee_id": s_emp, "customer_id": acct,
                              "relationship_type": "reviewer"})
    labeled_scenarios.append({
        "scenario_id": "L12",
        "scenario_type": "legitimate",
        "account_id": f"{s_acct_l12a};{s_acct_l12b}",
        "employee_id": s_emp,
        "description": "Year-end compliance: batch update of tax classifications "
                       "for IRS reporting deadline. All changes are W-9 verifications. "
                       "Compliance team directive with audit trail.",
        "related_event_ids": f"{evt_id_l12a};{evt_id_l12b}",
        "related_transaction_ids": "",
        "has_transactional_consequence": False,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L13: Authorized large donation — verified charitable giving
    s_acct = scenario_accounts[33]
    s_emp = scenario_employees[30]["employee_id"]
    base_time = _compute_base_time("L13")
    evt_id_l13 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l13,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "wire_transfer_limit=25000",
        "new_value": "wire_transfer_limit=500000",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L13",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L13",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Year-end charitable donation: high-net-worth customer makes "
                       "$300K donation to registered 501(c)(3). Wire limit increased "
                       "with documentation (gift letter, charity registration). "
                       "Consistent with customer's annual giving pattern.",
        "related_event_ids": evt_id_l13,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L14: Corporate card setup — new payee additions for approved cards
    s_acct = scenario_accounts[34]
    s_emp = scenario_employees[31]["employee_id"]
    base_time = _compute_base_time("L14")
    evt_id_l14 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l14,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "payees=[existing_vendors]",
        "new_value": "payees=[existing_vendors, VENDOR_X, VENDOR_Y, VENDOR_Z]",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L14",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L14",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Corporate procurement: new vendor additions for Q2 supply "
                       "contracts. All vendors verified through standard vendor "
                       "onboarding process. Purchase orders and contracts on file.",
        "related_event_ids": evt_id_l14,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L15: Verified real estate purchase — large authorized property transaction
    s_acct = scenario_accounts[35]
    s_emp = scenario_employees[32]["employee_id"]
    base_time = _compute_base_time("L15")
    evt_id_l15 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l15,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "wire_transfer_limit=50000",
        "new_value": "wire_transfer_limit=1000000",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L15",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L15",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Customer purchasing residential property: wire limit increased "
                       "for closing escrow payment of $850K. Title company details "
                       "verified. Single large wire to known escrow agent. Limit "
                       "auto-reverts after transaction.",
        "related_event_ids": evt_id_l15,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L16: Risk re-rating — annual review with supporting documentation
    s_acct = scenario_accounts[36]
    s_emp = scenario_employees[33]["employee_id"]
    base_time = _compute_base_time("L16")
    evt_id_l16 = next_evt_id()
    chg_id_l16 = next_chg_id()
    access_events.append({
        "event_id": evt_id_l16,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "risk_rating=high",
        "new_value": "risk_rating=medium",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L16",
    })
    profile_changes.append({
        "change_id": chg_id_l16,
        "customer_id": s_acct,
        "field_changed": "risk_rating",
        "old_value": "high",
        "new_value": "medium",
        "changed_by_employee_id": s_emp,
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "reviewer"})
    labeled_scenarios.append({
        "scenario_id": "L16",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Annual risk review: customer originally rated high due to "
                       "industry (cash-intensive business). 3-year clean record with "
                       "consistent patterns. Downgraded to medium per policy. "
                       "Risk committee approval documented.",
        "related_event_ids": evt_id_l16,
        "related_transaction_ids": "",
        "has_transactional_consequence": False,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L17: API access for verified fintech integration
    s_acct = scenario_accounts[37]
    s_emp = scenario_employees[34]["employee_id"]
    base_time = _compute_base_time("L17")
    evt_id_l17 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l17,
        "employee_id": s_emp,
        "action": "grant",
        "target_account_id": s_acct,
        "old_value": "",
        "new_value": "api_access",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L17",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "approver"})
    labeled_scenarios.append({
        "scenario_id": "L17",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Business customer integrates accounting software (QuickBooks) "
                       "via API. Fintech partner pre-vetted by IT Security. API access "
                       "scoped to read-only + scheduled payments. Proper OAuth setup.",
        "related_event_ids": evt_id_l17,
        "related_transaction_ids": "",
        "has_transactional_consequence": True,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    # L18: Standard spending limit review — annual inflation adjustment
    s_acct = scenario_accounts[38]
    s_emp = scenario_employees[35]["employee_id"]
    base_time = _compute_base_time("L18")
    evt_id_l18 = next_evt_id()
    access_events.append({
        "event_id": evt_id_l18,
        "employee_id": s_emp,
        "action": "modify",
        "target_account_id": s_acct,
        "old_value": "spending_limit=15000",
        "new_value": "spending_limit=17000",
        "timestamp": base_time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_type": "legitimate",
        "scenario_id": "L18",
    })
    relationships.append({"employee_id": s_emp, "customer_id": s_acct,
                          "relationship_type": "account_manager"})
    labeled_scenarios.append({
        "scenario_id": "L18",
        "scenario_type": "legitimate",
        "account_id": s_acct,
        "employee_id": s_emp,
        "description": "Annual CPI adjustment: spending limits for consumer accounts "
                       "increased ~13% to match inflation. Bank-wide policy change "
                       "applied systematically. No individual customer request needed.",
        "related_event_ids": evt_id_l18,
        "related_transaction_ids": "",
        "has_transactional_consequence": False,
    })
    labeled_scenarios[-1]["_base_time"] = base_time

    return access_events, profile_changes, labeled_scenarios, relationships


# ─── Main Execution ──────────────────────────────────────────────────────────



def generate_scenario_transactions(labeled_scenarios, account_ids):
    """Generate synthetic transaction rows matching each scenario's narrative.

    For each scenario with has_transactional_consequence=True and an entry
    in SCENARIO_TXN_CONFIG, generate the specified number of transactions
    with amounts, currencies, and formats matching the description.

    Returns:
        (list of transaction dicts, updated labeled_scenarios with IDs filled)
    """
    all_txns = []
    syn_counter = 0

    # Pick destination accounts from real IBM AML IDs
    dest_accounts = account_ids[200:500]  # Separate pool for destinations

    for scenario in labeled_scenarios:
        sid = scenario["scenario_id"]
        if not scenario.get("has_transactional_consequence", True):
            scenario["related_transaction_ids"] = ""
            continue
        if sid not in SCENARIO_TXN_CONFIG:
            scenario["related_transaction_ids"] = ""
            continue

        cfg = SCENARIO_TXN_CONFIG[sid]
        count = cfg["count"]
        amt_lo, amt_hi = cfg["amount_range"]
        currency = cfg["currency"]
        fmt = cfg["payment_format"]
        is_launder = cfg["is_laundering"]
        recv_currencies = cfg.get("receiving_currencies", None)

        # Parse account IDs for this scenario (may be semicolon-separated)
        acct_ids = [a.strip() for a in str(scenario["account_id"]).split(";")]
        from_acct = acct_ids[0]  # Primary sender

        # Get the access event base_time from the scenario's _base_time
        base_time = scenario.get("_base_time")
        if base_time is None:
            scenario["related_transaction_ids"] = ""
            continue

        # Get the gap for this scenario
        min_gap_h, max_gap_h = SCENARIO_TIMING[sid]

        # Generate transactions spread between base_time + small_offset and base_time + max_gap
        txn_ids = []
        for j in range(count):
            syn_counter += 1
            txn_id = f"SYN_{sid}_{j+1:03d}"
            txn_ids.append(txn_id)

            # Spread transactions across the gap window
            offset_min = min_gap_h * 3600  # seconds
            offset_max = max_gap_h * 3600
            # Even spread with jitter
            if count > 1:
                slot = offset_min + (offset_max - offset_min) * (j / (count - 1))
                jitter = random.uniform(-300, 300)  # ±5 min jitter
                offset = max(offset_min, slot + jitter)
            else:
                offset = random.uniform(offset_min, offset_max)

            txn_time = base_time + timedelta(seconds=offset)

            # Amount with slight randomization
            amount = round(random.uniform(amt_lo, amt_hi), 2)

            # For multi-account scenarios (S16), rotate through accounts
            if len(acct_ids) > 1:
                from_acct = acct_ids[j % len(acct_ids)]

            # Destination account
            to_acct = random.choice(dest_accounts)

            # Receiving currency
            if recv_currencies:
                recv_curr = recv_currencies[j % len(recv_currencies)]
            else:
                recv_curr = currency

            txn = {
                "transaction_id": txn_id,
                "timestamp": txn_time.strftime("%Y/%m/%d %H:%M"),
                "from_bank": random.randint(1, 500),
                "from_account": from_acct,
                "to_bank": random.randint(1, 500),
                "to_account": to_acct,
                "amount_received": amount,
                "receiving_currency": recv_curr,
                "amount_paid": amount,
                "payment_currency": currency,
                "payment_format": fmt,
                "is_laundering": is_launder,
                "source": "synthetic_scenario",
                "scenario_id": sid,
            }
            all_txns.append(txn)

        scenario["related_transaction_ids"] = ",".join(txn_ids)

    return all_txns, labeled_scenarios


def main():
    print("=" * 70)
    print("FIN04 Synthetic HR/Access Data Generator")
    print("=" * 70)
    print()

    # 1. Load real account IDs
    print("[1/8] Loading real account IDs from IBM AML data...")
    real_account_ids = load_real_account_ids()

    # 2. Generate employees
    print("[2/8] Generating employees...")
    employees = generate_employees(NUM_EMPLOYEES)

    # 3. Generate background data
    print("[3/8] Generating background access events...")
    bg_access = generate_background_access_events(
        employees, real_account_ids, NUM_BACKGROUND_ACCESS_EVENTS, start_id=1
    )

    print("[4/8] Generating background profile changes...")
    bg_profile = generate_background_profile_changes(
        employees, real_account_ids, NUM_BACKGROUND_PROFILE_CHANGES, start_id=1
    )

    bg_rels = generate_background_relationships(
        employees, real_account_ids, NUM_BACKGROUND_RELATIONSHIPS
    )

    # 4. Generate correlated scenarios
    print("[5/8] Generating correlated scenarios (18 suspicious + 18 legitimate)...")
    sc_access, sc_profile, labeled_scenarios, sc_rels = generate_correlated_scenarios(
        employees, real_account_ids
    )

    # 5. Generate injected transactions matching scenario narratives
    print("[6/8] Generating scenario transactions...")
    injected_txns, labeled_scenarios = generate_scenario_transactions(
        labeled_scenarios, real_account_ids
    )
    print(f"  Generated {len(injected_txns)} injected transactions")

    # 6. Merge background + scenario data
    all_access = bg_access + sc_access
    all_profile = bg_profile + sc_profile
    all_rels = bg_rels + sc_rels

    # Deduplicate relationships
    seen_rels = set()
    deduped_rels = []
    for r in all_rels:
        key = (r["employee_id"], r["customer_id"])
        if key not in seen_rels:
            seen_rels.add(key)
            deduped_rels.append(r)

    # Sort by timestamp
    all_access.sort(key=lambda x: x["timestamp"])
    all_profile.sort(key=lambda x: x["timestamp"])

    # 6. Write output files
    print("[7/8] Writing output files...")

    # employees.csv
    emp_df = pd.DataFrame(employees)
    emp_df.to_csv(OUTPUT_DIR / "employees.csv", index=False)
    print(f"  employees.csv: {len(emp_df)} rows")

    # access_events.csv
    acc_df = pd.DataFrame(all_access)
    acc_df.to_csv(OUTPUT_DIR / "access_events.csv", index=False)
    print(f"  access_events.csv: {len(acc_df)} rows")

    # profile_changes.csv
    prof_df = pd.DataFrame(all_profile)
    prof_df.to_csv(OUTPUT_DIR / "profile_changes.csv", index=False)
    print(f"  profile_changes.csv: {len(prof_df)} rows")

    # employee_customer_map.csv
    rel_df = pd.DataFrame(deduped_rels)
    rel_df.to_csv(OUTPUT_DIR / "employee_customer_map.csv", index=False)
    print(f"  employee_customer_map.csv: {len(rel_df)} rows")

    # labeled_scenarios.csv — strip internal _base_time before writing
    for s in labeled_scenarios:
        s.pop("_base_time", None)
    sc_df = pd.DataFrame(labeled_scenarios)
    sc_df.to_csv(OUTPUT_DIR / "labeled_scenarios.csv", index=False)
    print(f"  labeled_scenarios.csv: {len(sc_df)} rows")

    # injected_transactions.csv
    if injected_txns:
        inj_df = pd.DataFrame(injected_txns)
        inj_df.to_csv(OUTPUT_DIR / "injected_transactions.csv", index=False)
        print(f"  injected_transactions.csv: {len(inj_df)} rows")
    else:
        print("  injected_transactions.csv: 0 rows (no transactions generated)")

    # Summary
    print()
    print("Summary:")
    print(f"  Employees:              {len(employees)}")
    print(f"  Access events:          {len(all_access)}")
    print(f"    - Background:         {len(bg_access)}")
    print(f"    - Scenario:           {len(sc_access)}")
    print(f"  Profile changes:        {len(all_profile)}")
    print(f"    - Background:         {len(bg_profile)}")
    print(f"    - Scenario:           {len(sc_profile)}")
    print(f"  Relationships:          {len(deduped_rels)}")
    print(f"  Labeled scenarios:      {len(labeled_scenarios)}")
    print(f"  Injected transactions:  {len(injected_txns)}")
    suspicious = sum(1 for s in labeled_scenarios if s["scenario_type"] == "suspicious")
    legitimate = sum(1 for s in labeled_scenarios if s["scenario_type"] == "legitimate")
    print(f"    - Suspicious:         {suspicious}")
    print(f"    - Legitimate:         {legitimate}")
    # 8. Quick self-check
    print()
    print("[8/8] Self-check...")
    htc_true = sum(1 for s in labeled_scenarios
                   if s.get("has_transactional_consequence", True) is True)
    htc_false = sum(1 for s in labeled_scenarios
                    if s.get("has_transactional_consequence", False) is False)
    has_txn_ids = sum(1 for s in labeled_scenarios
                      if s.get("related_transaction_ids", "") != "")
    print(f"  has_transactional_consequence=True:  {htc_true}")
    print(f"  has_transactional_consequence=False: {htc_false}")
    print(f"  Scenarios with related_transaction_ids: {has_txn_ids}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
