"""
Build Graph Construction Input:
- data/graph/nodes.csv
- data/graph/edges.csv
"""

import sys
import json
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"c:\Users\HP\OneDrive\المستندات\Projects\HackMatrix\data")
GRAPH_DIR = DATA_DIR / "graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

print("Step 1: Loading entities, synthetic HR, and transaction files...")
df_employees = pd.read_csv(DATA_DIR / "synthetic_hr" / "employees.csv")
df_customers = pd.read_csv(DATA_DIR / "entities" / "customers.csv")
df_accounts = pd.read_csv(DATA_DIR / "entities" / "accounts.csv")
df_inj = pd.read_csv(DATA_DIR / "synthetic_hr" / "injected_transactions.csv")
df_real_in_scope = pd.read_csv(DATA_DIR / "entities" / "in_scope_real_transactions.csv")

df_ec_map = pd.read_csv(DATA_DIR / "synthetic_hr" / "employee_customer_map.csv")
df_access = pd.read_csv(DATA_DIR / "synthetic_hr" / "access_events.csv")
df_profile = pd.read_csv(DATA_DIR / "synthetic_hr" / "profile_changes.csv")
df_scenarios = pd.read_csv(DATA_DIR / "synthetic_hr" / "labeled_scenarios.csv")

# 1. Identify transactions to include as graph nodes:
# - All 211 injected transactions
# - Real transactions linked to labeled scenarios or access events
print("\nStep 2: Selecting investigation-relevant transactions...")
# Scenario accounts
scen_accs = set()
for a in df_scenarios['account_id'].dropna():
    for sub in str(a).split(';'):
        if sub.strip():
            scen_accs.add(sub.strip())

# Access event accounts
access_accs = set()
for a in df_access['target_account_id'].dropna():
    for sub in str(a).split(';'):
        if sub.strip():
            access_accs.add(sub.strip())

investigation_accs = scen_accs | access_accs
print(f"Investigation accounts (scenarios + access events): {len(investigation_accs)}")

# Filter real transactions involving investigation accounts
m_real = df_real_in_scope['from_account'].astype(str).isin(investigation_accs) | \
         df_real_in_scope['to_account'].astype(str).isin(investigation_accs)
df_real_investigation = df_real_in_scope[m_real].copy()
df_real_investigation['is_synthetic'] = False
df_real_investigation['source'] = 'ibm_aml'

df_inj_tx = df_inj.copy()
df_inj_tx['is_synthetic'] = True

print(f"Selected {len(df_inj_tx)} synthetic transactions")
print(f"Selected {len(df_real_investigation)} real investigation transactions")
total_investigation_txns = pd.concat([
    df_inj_tx[['transaction_id', 'timestamp', 'from_account', 'to_account', 
               'amount_paid', 'payment_currency', 'payment_format', 'is_laundering', 'is_synthetic']],
    df_real_investigation[['transaction_id', 'timestamp', 'from_account', 'to_account', 
                          'amount_paid', 'payment_currency', 'payment_format', 'is_laundering', 'is_synthetic']]
], ignore_index=True)

# 2. Build Nodes
print("\nStep 3: Building nodes.csv...")
nodes = []

# Employee nodes
for _, emp in df_employees.iterrows():
    nodes.append({
        "node_id": str(emp['employee_id']),
        "node_type": "Employee",
        "label": f"{emp['name']} ({emp['role']}, {emp['department']})"
    })

# Customer nodes
for _, cust in df_customers.iterrows():
    nodes.append({
        "node_id": str(cust['customer_id']),
        "node_type": "Customer",
        "label": f"{cust['name']} ({cust['country']}, Risk: {cust['risk_rating']})"
    })

# Account nodes (from Part 1)
part1_account_ids = set()
for _, acc in df_accounts.iterrows():
    acc_id = str(acc['account_id'])
    part1_account_ids.add(acc_id)
    bank_info = f"Bank {acc['bank_id']}" if pd.notna(acc['bank_id']) and acc['bank_id'] != "" else "Unknown Bank"
    nodes.append({
        "node_id": acc_id,
        "node_type": "Account",
        "label": f"Account {acc_id} ({bank_info})"
    })

# Also include any external counterparty accounts participating in the included transactions
# to ensure graph referential integrity (no dangling edges)
all_txn_accounts = set(total_investigation_txns['from_account'].astype(str)) | \
                   set(total_investigation_txns['to_account'].astype(str))
external_counterparties = all_txn_accounts - part1_account_ids
print(f"Adding {len(external_counterparties)} external counterparty accounts to prevent dangling edges")
for ext_acc in sorted(external_counterparties):
    nodes.append({
        "node_id": ext_acc,
        "node_type": "Account",
        "label": f"Account {ext_acc} (External Counterparty)"
    })

# Transaction nodes
for _, tx in total_investigation_txns.iterrows():
    src_tag = "SYNTHETIC" if tx['is_synthetic'] else "REAL"
    amt = float(tx['amount_paid']) if pd.notna(tx['amount_paid']) else 0.0
    curr = str(tx['payment_currency']) if pd.notna(tx['payment_currency']) else "USD"
    fmt = str(tx['payment_format']) if pd.notna(tx['payment_format']) else "Payment"
    nodes.append({
        "node_id": str(tx['transaction_id']),
        "node_type": "Transaction",
        "label": f"[{src_tag}] {tx['transaction_id']}: {amt:,.2f} {curr} via {fmt}"
    })

df_nodes = pd.DataFrame(nodes)
nodes_path = GRAPH_DIR / "nodes.csv"
df_nodes.to_csv(nodes_path, index=False)
print(f"Saved {len(df_nodes)} nodes to {nodes_path}")

# 3. Build Edges
print("\nStep 4: Building edges.csv...")
edges = []

# Edge Type 1: OWNS (Customer -> Account)
for _, cust in df_customers.iterrows():
    cid = str(cust['customer_id'])
    accs_str = str(cust['account_ids'])
    for acc in accs_str.split(','):
        acc = acc.strip()
        if acc:
            edges.append({
                "source_id": cid,
                "target_id": acc,
                "edge_type": "OWNS",
                "timestamp": "",
                "metadata": json.dumps({"relationship": "owner"})
            })

# Edge Type 2: MANAGES (Employee -> Customer)
for _, ec in df_ec_map.iterrows():
    edges.append({
        "source_id": str(ec['employee_id']),
        "target_id": str(ec['customer_id']),
        "edge_type": "MANAGES",
        "timestamp": "",
        "metadata": json.dumps({"relationship_type": str(ec['relationship_type'])})
    })

# Edge Type 3: CHANGED_ACCESS (Employee -> Account)
for _, ev in df_access.iterrows():
    target = str(ev['target_account_id'])
    for t_sub in target.split(';'):
        t_sub = t_sub.strip()
        if t_sub:
            edges.append({
                "source_id": str(ev['employee_id']),
                "target_id": t_sub,
                "edge_type": "CHANGED_ACCESS",
                "timestamp": str(ev['timestamp']),
                "metadata": json.dumps({
                    "event_id": str(ev['event_id']),
                    "action": str(ev['action']),
                    "old_value": str(ev.get('old_value', '')),
                    "new_value": str(ev.get('new_value', ''))
                })
            })

# Edge Type 4: EDITED_PROFILE (Employee -> Customer)
for _, pr in df_profile.iterrows():
    edges.append({
        "source_id": str(pr['changed_by_employee_id']),
        "target_id": str(pr['customer_id']),
        "edge_type": "EDITED_PROFILE",
        "timestamp": str(pr['timestamp']),
        "metadata": json.dumps({
            "change_id": str(pr['change_id']),
            "field_changed": str(pr['field_changed']),
            "old_value": str(pr.get('old_value', '')),
            "new_value": str(pr.get('new_value', ''))
        })
    })

# Edge Type 5: SENT_TO (Account -> Account)
for _, tx in total_investigation_txns.iterrows():
    amt = float(tx['amount_paid']) if pd.notna(tx['amount_paid']) else 0.0
    edges.append({
        "source_id": str(tx['from_account']),
        "target_id": str(tx['to_account']),
        "edge_type": "SENT_TO",
        "timestamp": str(tx['timestamp']),
        "metadata": json.dumps({
            "transaction_id": str(tx['transaction_id']),
            "amount": amt,
            "currency": str(tx['payment_currency']),
            "format": str(tx['payment_format']),
            "is_laundering": int(tx['is_laundering']),
            "is_synthetic": bool(tx['is_synthetic'])
        })
    })

# Edge Type 6: INVOLVED_IN (Account -> Transaction, role: sender/receiver)
for _, tx in total_investigation_txns.iterrows():
    tx_id = str(tx['transaction_id'])
    fa = str(tx['from_account'])
    ta = str(tx['to_account'])
    ts = str(tx['timestamp'])
    amt = float(tx['amount_paid']) if pd.notna(tx['amount_paid']) else 0.0
    
    # Sender -> Transaction
    edges.append({
        "source_id": fa,
        "target_id": tx_id,
        "edge_type": "INVOLVED_IN",
        "timestamp": ts,
        "metadata": json.dumps({"role": "sender", "amount": amt})
    })
    # Receiver -> Transaction
    edges.append({
        "source_id": ta,
        "target_id": tx_id,
        "edge_type": "INVOLVED_IN",
        "timestamp": ts,
        "metadata": json.dumps({"role": "receiver", "amount": amt})
    })

df_edges = pd.DataFrame(edges)
edges_path = GRAPH_DIR / "edges.csv"
df_edges.to_csv(edges_path, index=False)
print(f"Saved {len(df_edges)} edges to {edges_path}")

print("\n=== SUMMARY STATISTICS ===")
print("\n--- Node Counts by Type ---")
print(df_nodes['node_type'].value_counts().to_string())

print("\n--- Edge Counts by Type ---")
print(df_edges['edge_type'].value_counts().to_string())
