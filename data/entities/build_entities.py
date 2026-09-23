"""
Build Canonical Entity Tables:
- data/entities/accounts.csv
- data/entities/customers.csv
- data/entities/in_scope_real_transactions.csv (for fast O(1) graph & history lookup)
"""

import sys
import random
from pathlib import Path
import pandas as pd
from faker import Faker

sys.stdout.reconfigure(encoding='utf-8')

# Ensure deterministic generation
Faker.seed(42)
random.seed(42)
fake = Faker()

DATA_DIR = Path(r"c:\Users\HP\OneDrive\المستندات\Projects\HackMatrix\data")
ENTITIES_DIR = DATA_DIR / "entities"
ENTITIES_DIR.mkdir(parents=True, exist_ok=True)

print("Step 1: Loading synthetic HR and scenario files...")
acc_ev = pd.read_csv(DATA_DIR / "synthetic_hr" / "access_events.csv")
scen = pd.read_csv(DATA_DIR / "synthetic_hr" / "labeled_scenarios.csv")
inj = pd.read_csv(DATA_DIR / "synthetic_hr" / "injected_transactions.csv")
ec_map = pd.read_csv(DATA_DIR / "synthetic_hr" / "employee_customer_map.csv")
prof = pd.read_csv(DATA_DIR / "synthetic_hr" / "profile_changes.csv")

# 1. Scope Customers: customer_ids that appear in employee_customer_map or profile_changes
cust_ids = set()
for c in ec_map['customer_id'].dropna():
    for sub in str(c).split(';'):
        if sub.strip():
            cust_ids.add(sub.strip())
for c in prof['customer_id'].dropna():
    for sub in str(c).split(';'):
        if sub.strip():
            cust_ids.add(sub.strip())

sorted_cust_ids = sorted(cust_ids)
print(f"Total unique customers in scope: {len(sorted_cust_ids)}")

# 2. Scope Accounts: access_events.target_account_id, labeled_scenarios.account_id,
# injected_transactions.from_account/to_account, and customer accounts
account_ids = set()
for a in acc_ev['target_account_id'].dropna():
    for sub in str(a).split(';'):
        if sub.strip():
            account_ids.add(sub.strip())
for a in scen['account_id'].dropna():
    for sub in str(a).split(';'):
        if sub.strip():
            account_ids.add(sub.strip())
for a in inj['from_account'].dropna():
    account_ids.add(str(a).strip())
for a in inj['to_account'].dropna():
    account_ids.add(str(a).strip())
for c in cust_ids:
    account_ids.add(c)

sorted_account_ids = sorted(account_ids)
print(f"Total unique accounts in scope: {len(sorted_account_ids)}")

# 3. Build customers.csv
print("\nStep 2: Building customers.csv...")
customer_rows = []
risk_choices = ["Low", "Medium", "High"]
risk_weights = [0.75, 0.20, 0.05]

for cid in sorted_cust_ids:
    name = fake.name()
    country = fake.country()
    risk = random.choices(risk_choices, weights=risk_weights, k=1)[0]
    # In this dataset, customer cid owns account cid (1:1 mapping)
    linked_accs = cid if cid in account_ids else ""
    customer_rows.append({
        "customer_id": cid,
        "name": name,
        "country": country,
        "account_ids": linked_accs,
        "risk_rating": risk
    })

df_customers = pd.DataFrame(customer_rows)
cust_path = ENTITIES_DIR / "customers.csv"
df_customers.to_csv(cust_path, index=False)
print(f"Saved {len(df_customers)} customers to {cust_path}")

# 4. Scan transactions_clean.csv to extract real transaction stats for in-scope accounts
print("\nStep 3: Scanning transactions_clean.csv for in-scope accounts...")
real_extracted_path = ENTITIES_DIR / "in_scope_real_transactions.csv"

if real_extracted_path.exists():
    print(f"Loading cached real transactions from {real_extracted_path}...")
    df_in_scope_real = pd.read_csv(real_extracted_path)
else:
    chunk_size = 500000
    clean_path = DATA_DIR / "ibm_aml" / "transactions_clean.csv"
    real_txns_list = []
    for chunk in pd.read_csv(clean_path, chunksize=chunk_size, 
                             usecols=['transaction_id', 'timestamp', 'from_bank', 'from_account', 
                                      'to_bank', 'to_account', 'amount_paid', 'payment_currency', 
                                      'payment_format', 'is_laundering']):
        fa_str = chunk['from_account'].astype(str)
        ta_str = chunk['to_account'].astype(str)
        m = fa_str.isin(account_ids) | ta_str.isin(account_ids)
        sub = chunk[m].copy()
        if not sub.empty:
            real_txns_list.append(sub)
    df_in_scope_real = pd.concat(real_txns_list, ignore_index=True)
    df_in_scope_real.to_csv(real_extracted_path, index=False)
    print(f"Saved {len(df_in_scope_real)} real transactions to {real_extracted_path}")

# Vectorized aggregation for real transactions
print("Aggregating real transaction statistics...")
df_in_scope_real['from_account'] = df_in_scope_real['from_account'].astype(str)
df_in_scope_real['to_account'] = df_in_scope_real['to_account'].astype(str)
df_in_scope_real['timestamp'] = df_in_scope_real['timestamp'].astype(str)

# From side
from_m = df_in_scope_real[df_in_scope_real['from_account'].isin(account_ids)]
from_grp = from_m.groupby('from_account').agg(
    count=('transaction_id', 'count'),
    first_ts=('timestamp', 'min'),
    last_ts=('timestamp', 'max'),
    bank_id=('from_bank', 'first')
).to_dict('index')

# To side
to_m = df_in_scope_real[df_in_scope_real['to_account'].isin(account_ids)]
to_grp = to_m.groupby('to_account').agg(
    count=('transaction_id', 'count'),
    first_ts=('timestamp', 'min'),
    last_ts=('timestamp', 'max'),
    bank_id=('to_bank', 'first')
).to_dict('index')

# Self-transfers (from_account == to_account): must NOT be double-counted!
self_m = df_in_scope_real[(df_in_scope_real['from_account'] == df_in_scope_real['to_account']) & 
                         (df_in_scope_real['from_account'].isin(account_ids))]
self_counts = self_m.groupby('from_account').size().to_dict()

# Real laundering transactions in background data
launder_m = df_in_scope_real[df_in_scope_real['is_laundering'] == 1]
from_l = launder_m[launder_m['from_account'].isin(account_ids)].groupby('from_account').size()
to_l = launder_m[launder_m['to_account'].isin(account_ids)].groupby('to_account').size()
self_l = launder_m[(launder_m['from_account'] == launder_m['to_account']) & 
                   (launder_m['from_account'].isin(account_ids))].groupby('from_account').size()

# 5. Process synthetic / injected transactions
print("\nStep 4: Incorporating synthetic / injected transactions...")
inj['from_account'] = inj['from_account'].astype(str)
inj['to_account'] = inj['to_account'].astype(str)
inj['timestamp'] = inj['timestamp'].astype(str)

inj_from = inj[inj['from_account'].isin(account_ids)].groupby('from_account').agg(
    count=('transaction_id', 'count'),
    first_ts=('timestamp', 'min'),
    last_ts=('timestamp', 'max'),
    bank_id=('from_bank', 'first')
).to_dict('index')

inj_to = inj[inj['to_account'].isin(account_ids)].groupby('to_account').agg(
    count=('transaction_id', 'count'),
    first_ts=('timestamp', 'min'),
    last_ts=('timestamp', 'max'),
    bank_id=('to_bank', 'first')
).to_dict('index')

inj_self = inj[(inj['from_account'] == inj['to_account']) & (inj['from_account'].isin(account_ids))]
inj_self_counts = inj_self.groupby('from_account').size().to_dict()

# 6. Build accounts.csv
print("\nStep 5: Building accounts.csv...")
account_rows = []
for acc in sorted_account_ids:
    linked_cust = acc if acc in cust_ids else ""
    
    # Real stats: Distinct transaction row count = count(from) + count(to) - count(self)
    fc = from_grp.get(acc, {}).get('count', 0)
    tc = to_grp.get(acc, {}).get('count', 0)
    sc = self_counts.get(acc, 0)
    r_count = fc + tc - sc
    
    # Background real laundering count
    fl = from_l.get(acc, 0)
    tl = to_l.get(acc, 0)
    sl = self_l.get(acc, 0)
    bg_launder_count = fl + tl - sl
    
    # Synthetic stats: Distinct transaction row count
    ifc = inj_from.get(acc, {}).get('count', 0)
    itc = inj_to.get(acc, {}).get('count', 0)
    isc = inj_self_counts.get(acc, 0)
    s_count = ifc + itc - isc
    
    # Bank ID (prefer real transaction bank, fallback to injected)
    f_stat = from_grp.get(acc, {})
    t_stat = to_grp.get(acc, {})
    if_stat = inj_from.get(acc, {})
    it_stat = inj_to.get(acc, {})
    bank = f_stat.get('bank_id', t_stat.get('bank_id', if_stat.get('bank_id', it_stat.get('bank_id', ""))))
    
    # Timestamps
    all_ts = [
        f_stat.get('first_ts'), f_stat.get('last_ts'),
        t_stat.get('first_ts'), t_stat.get('last_ts'),
        if_stat.get('first_ts'), if_stat.get('last_ts'),
        it_stat.get('first_ts'), it_stat.get('last_ts')
    ]
    valid_ts = [t for t in all_ts if t]
    first_ts = min(valid_ts) if valid_ts else ""
    last_ts = max(valid_ts) if valid_ts else ""
    
    account_rows.append({
        "account_id": acc,
        "linked_customer_id": linked_cust,
        "bank_id": bank,
        "first_seen_timestamp": first_ts,
        "last_seen_timestamp": last_ts,
        "real_txn_count": r_count,
        "synthetic_txn_count": s_count,
        "total_transaction_count": r_count + s_count,
        "background_real_laundering_count": bg_launder_count
    })

df_accounts = pd.DataFrame(account_rows)
acc_path = ENTITIES_DIR / "accounts.csv"
df_accounts.to_csv(acc_path, index=False)
print(f"Saved {len(df_accounts)} accounts to {acc_path}")

print("\n=== COMPLETE ===")
print(f"df_accounts: {len(df_accounts)} rows, {df_accounts.shape[1]} columns")
print(f"df_customers: {len(df_customers)} rows, {df_customers.shape[1]} columns")
