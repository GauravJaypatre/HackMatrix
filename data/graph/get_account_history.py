"""
get_account_history.py — Unified Investigation Query Utility

Provides a single function get_account_history(account_id) that returns:
- the account's own record (from accounts.csv)
- the linked customer record (if any)
- the linked employee(s) with a relationship to that customer (from employee_customer_map)
- all access_events targeting this account, sorted by timestamp
- all profile_changes for the linked customer, sorted by timestamp
- all transactions (real AND injected, clearly labeled) involving this account as sender or receiver, sorted by timestamp
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd

# Path configuration
BASE_DIR = Path(__file__).resolve().parent.parent
ENTITIES_DIR = BASE_DIR / "entities"
HR_DIR = BASE_DIR / "synthetic_hr"
IBM_DIR = BASE_DIR / "ibm_aml"

# Lazy-loaded in-memory cache for fast repeated queries
_DATA_CACHE = {}


def _get_data():
    """Load and cache dataframes once for sub-second queries."""
    if not _DATA_CACHE:
        _DATA_CACHE['accounts'] = pd.read_csv(ENTITIES_DIR / "accounts.csv")
        _DATA_CACHE['customers'] = pd.read_csv(ENTITIES_DIR / "customers.csv")
        _DATA_CACHE['employees'] = pd.read_csv(HR_DIR / "employees.csv")
        _DATA_CACHE['ec_map'] = pd.read_csv(HR_DIR / "employee_customer_map.csv")
        _DATA_CACHE['access_events'] = pd.read_csv(HR_DIR / "access_events.csv")
        _DATA_CACHE['profile_changes'] = pd.read_csv(HR_DIR / "profile_changes.csv")
        _DATA_CACHE['injected_txns'] = pd.read_csv(HR_DIR / "injected_transactions.csv")
        
        # Real in-scope transactions extracted during canonical entity build
        real_tx_path = ENTITIES_DIR / "in_scope_real_transactions.csv"
        if real_tx_path.exists():
            _DATA_CACHE['real_txns'] = pd.read_csv(real_tx_path)
        else:
            _DATA_CACHE['real_txns'] = pd.DataFrame()
            
    return _DATA_CACHE


def get_account_history(account_id: str) -> Dict[str, Any]:
    """
    Retrieve the full unified investigation history for a given account_id.
    
    Args:
        account_id: The bank account ID (e.g. '800056370')
        
    Returns:
        dict containing:
          - account: dict from accounts.csv
          - customer: dict from customers.csv (or None)
          - employees: list of linked employee dicts
          - access_events: list of access events on this account, sorted by timestamp
          - profile_changes: list of profile changes for linked customer, sorted by timestamp
          - transactions: list of real + injected transactions, sorted by timestamp
          - summary: summary counts of events, changes, and transactions
    """
    data = _get_data()
    acc_id = str(account_id).strip()
    
    # 1. Account Record
    acc_df = data['accounts']
    matching_acc = acc_df[acc_df['account_id'].astype(str) == acc_id]
    if matching_acc.empty:
        account_record = None
        linked_customer_id = None
    else:
        account_record = matching_acc.iloc[0].to_dict()
        # Clean NaNs
        account_record = {k: (None if pd.isna(v) else v) for k, v in account_record.items()}
        linked_customer_id = account_record.get('linked_customer_id')
        if linked_customer_id == "" or pd.isna(linked_customer_id):
            linked_customer_id = None
            
    # 2. Customer Record
    customer_record = None
    if linked_customer_id:
        cust_df = data['customers']
        matching_cust = cust_df[cust_df['customer_id'].astype(str) == str(linked_customer_id)]
        if not matching_cust.empty:
            customer_record = matching_cust.iloc[0].to_dict()
            customer_record = {k: (None if pd.isna(v) else v) for k, v in customer_record.items()}
            
    # 3. Linked Employee(s)
    linked_employees = []
    if linked_customer_id:
        ec_df = data['ec_map']
        emp_df = data['employees']
        matching_ec = ec_df[ec_df['customer_id'].astype(str) == str(linked_customer_id)]
        for _, ec_row in matching_ec.iterrows():
            emp_id = str(ec_row['employee_id'])
            rel_type = str(ec_row['relationship_type'])
            emp_match = emp_df[emp_df['employee_id'].astype(str) == emp_id]
            if not emp_match.empty:
                emp_dict = emp_match.iloc[0].to_dict()
                emp_dict['relationship_type'] = rel_type
                linked_employees.append(emp_dict)
            else:
                linked_employees.append({
                    "employee_id": emp_id,
                    "relationship_type": rel_type
                })
                
    # 4. Access Events targeting this account
    access_df = data['access_events']
    # Check exact match or semicolon contained
    ev_mask = access_df['target_account_id'].dropna().astype(str).apply(
        lambda x: acc_id in [sub.strip() for sub in x.split(';')]
    )
    matching_events = access_df[ev_mask].copy()
    if not matching_events.empty:
        matching_events['timestamp'] = matching_events['timestamp'].astype(str)
        matching_events = matching_events.sort_values('timestamp')
        access_events_list = [
            {k: (None if pd.isna(v) else v) for k, v in r.items()}
            for r in matching_events.to_dict('records')
        ]
    else:
        access_events_list = []
        
    # 5. Profile Changes for the linked customer
    profile_df = data['profile_changes']
    if linked_customer_id:
        prof_mask = profile_df['customer_id'].astype(str) == str(linked_customer_id)
        matching_prof = profile_df[prof_mask].copy()
        if not matching_prof.empty:
            matching_prof['timestamp'] = matching_prof['timestamp'].astype(str)
            matching_prof = matching_prof.sort_values('timestamp')
            profile_changes_list = [
                {k: (None if pd.isna(v) else v) for k, v in r.items()}
                for r in matching_prof.to_dict('records')
            ]
        else:
            profile_changes_list = []
    else:
        profile_changes_list = []
        
    # 6. Transactions (real AND injected)
    all_txns = []
    
    # Helper to assign precise role
    def determine_role(fa: str, ta: str) -> str:
        is_sender = (fa == acc_id)
        is_receiver = (ta == acc_id)
        if is_sender and is_receiver:
            return 'self'  # Account transferred to itself (reinvestment/internal)
        elif is_sender:
            return 'sender'
        elif is_receiver:
            return 'receiver'
        else:
            return 'unrelated'

    # Injected / synthetic transactions
    inj_df = data['injected_txns']
    inj_mask = (inj_df['from_account'].astype(str) == acc_id) | (inj_df['to_account'].astype(str) == acc_id)
    matching_inj = inj_df[inj_mask].copy()
    for _, tx in matching_inj.iterrows():
        tx_dict = tx.to_dict()
        tx_dict['is_synthetic'] = True
        tx_dict['source'] = 'synthetic_scenario'
        tx_dict['account_role'] = determine_role(str(tx['from_account']), str(tx['to_account']))
        all_txns.append({k: (None if pd.isna(v) else v) for k, v in tx_dict.items()})
        
    # Real transactions
    real_df = data['real_txns']
    if not real_df.empty:
        real_mask = (real_df['from_account'].astype(str) == acc_id) | (real_df['to_account'].astype(str) == acc_id)
        matching_real = real_df[real_mask].copy()
        for _, tx in matching_real.iterrows():
            tx_dict = tx.to_dict()
            tx_dict['is_synthetic'] = False
            tx_dict['source'] = 'ibm_aml'
            tx_dict['account_role'] = determine_role(str(tx['from_account']), str(tx['to_account']))
            all_txns.append({k: (None if pd.isna(v) else v) for k, v in tx_dict.items()})
            
    # Sort all transactions chronologically by timestamp
    all_txns.sort(key=lambda x: str(x.get('timestamp', '')))
    
    # Summary & Role counts
    synth_txns = [t for t in all_txns if t.get('is_synthetic')]
    real_txns = [t for t in all_txns if not t.get('is_synthetic')]
    
    sender_count = sum(1 for t in all_txns if t.get('account_role') == 'sender')
    receiver_count = sum(1 for t in all_txns if t.get('account_role') == 'receiver')
    self_count = sum(1 for t in all_txns if t.get('account_role') == 'self')
    
    summary = {
        "account_id": acc_id,
        "has_account_record": account_record is not None,
        "has_linked_customer": customer_record is not None,
        "linked_employee_count": len(linked_employees),
        "access_event_count": len(access_events_list),
        "profile_change_count": len(profile_changes_list),
        "total_transactions": len(all_txns),
        "synthetic_transactions": len(synth_txns),
        "real_transactions": len(real_txns),
        "role_counts": {
            "sender": sender_count,
            "receiver": receiver_count,
            "self": self_count
        }
    }
    
    return {
        "account_id": acc_id,
        "account": account_record,
        "customer": customer_record,
        "employees": linked_employees,
        "access_events": access_events_list,
        "profile_changes": profile_changes_list,
        "transactions": all_txns,
        "summary": summary
    }


def format_account_history_report(history: Dict[str, Any], max_txns_display: int = 25) -> str:
    """Format account history dictionary into a clear, structured text report."""
    acc = history.get('account') or {}
    cust = history.get('customer') or {}
    emps = history.get('employees') or []
    events = history.get('access_events') or []
    profs = history.get('profile_changes') or []
    txns = history.get('transactions') or []
    summ = history.get('summary') or {}
    roles = summ.get('role_counts') or {}
    
    lines = []
    lines.append("=" * 80)
    lines.append(f"UNIFIED INVESTIGATION REPORT: ACCOUNT {history['account_id']}")
    lines.append("=" * 80)
    
    # Reconciliation Status
    acc_tot = acc.get('total_transaction_count', 0)
    ledger_tot = summ.get('total_transactions', 0)
    acc_real = acc.get('real_txn_count', 0)
    ledger_real = summ.get('real_transactions', 0)
    acc_syn = acc.get('synthetic_txn_count', 0)
    ledger_syn = summ.get('synthetic_transactions', 0)
    reconciled = (acc_tot == ledger_tot and acc_real == ledger_real and acc_syn == ledger_syn)
    status_str = "✅ RECONCILED (100% MATCH)" if reconciled else "❌ MISMATCH"
    
    lines.append(f"\n[RECONCILIATION AUDIT]: {status_str}")
    lines.append(f"  Account Record:     Total={acc_tot} (Real={acc_real}, Synthetic={acc_syn})")
    lines.append(f"  Transaction Ledger: Total={ledger_tot} (Real={ledger_real}, Synthetic={ledger_syn})")
    lines.append(f"  Role Breakdown:     Sender={roles.get('sender', 0)} | Receiver={roles.get('receiver', 0)} | Self-Transfer={roles.get('self', 0)}")
    
    lines.append("\n[1] ACCOUNT MASTER RECORD")
    lines.append(f"  Account ID:             {acc.get('account_id')}")
    lines.append(f"  Linked Customer ID:     {acc.get('linked_customer_id')}")
    lines.append(f"  Bank ID:                {acc.get('bank_id')}")
    lines.append(f"  Activity Window:        {acc.get('first_seen_timestamp')}  -->  {acc.get('last_seen_timestamp')}")
    lines.append(f"  Total Transactions:     {acc_tot} (Real: {acc_real}, Synthetic: {acc_syn})")
    lines.append(f"  Background Laundering:  {acc.get('background_real_laundering_count', 0)} real transactions with is_laundering=1")
    
    lines.append("\n[2] LINKED CUSTOMER RECORD")
    if cust:
        lines.append(f"  Customer ID:            {cust.get('customer_id')}")
        lines.append(f"  Name:                   {cust.get('name')}")
        lines.append(f"  Country:                {cust.get('country')}")
        lines.append(f"  Risk Rating (demo):     {cust.get('risk_rating')}")
        lines.append(f"  Linked Accounts:        {cust.get('account_ids')}")
    else:
        lines.append("  No customer record linked.")
        
    lines.append("\n[3] LINKED EMPLOYEES (from employee_customer_map)")
    if emps:
        for e in emps:
            lines.append(f"  Employee: {e.get('employee_id')} | Name: {e.get('name', 'N/A')} | Role: {e.get('role', 'N/A')} | Department: {e.get('department', 'N/A')} | Relationship: {e.get('relationship_type')}")
    else:
        lines.append("  No employee relationships on record.")
        
    lines.append(f"\n[4] ACCESS EVENTS TARGETING THIS ACCOUNT ({len(events)} events)")
    if events:
        for ev in events:
            scen_info = f" [Scenario: {ev.get('scenario_id')}]" if ev.get('scenario_id') else ""
            lines.append(f"  [{ev.get('timestamp')}] {ev.get('event_id')} by {ev.get('employee_id')}: Action='{ev.get('action')}' | Old='{ev.get('old_value')}' -> New='{ev.get('new_value')}'{scen_info}")
    else:
        lines.append("  No access events found.")
        
    lines.append(f"\n[5] PROFILE CHANGES FOR LINKED CUSTOMER ({len(profs)} changes)")
    if profs:
        for pr in profs:
            lines.append(f"  [{pr.get('timestamp')}] {pr.get('change_id')} by Employee {pr.get('changed_by_employee_id')}: Field='{pr.get('field_changed')}' | Old='{pr.get('old_value')}' -> New='{pr.get('new_value')}'")
    else:
        lines.append("  No profile changes found.")
        
    lines.append(f"\n[6] TRANSACTION LEDGER ({len(txns)} total transactions: {ledger_syn} synthetic, {ledger_real} real)")
    lines.append(f"    Breakdown: {roles.get('sender', 0)} Pure Senders, {roles.get('receiver', 0)} Pure Receivers, {roles.get('self', 0)} Self-Transfers")
    
    if txns:
        # Include sample senders, sample self, all receivers, and all synthetic transactions
        # to ensure user can inspect every role in the output table
        receivers = [t for t in txns if t.get('account_role') == 'receiver']
        synthetics = [t for t in txns if t.get('is_synthetic')]
        selfs = [t for t in txns if t.get('account_role') == 'self'][:3]
        senders = [t for t in txns if t.get('account_role') == 'sender'][:10]
        
        # Display ordered selection
        displayed_set = set()
        display_order = []
        for group in [senders, selfs, receivers, synthetics]:
            for t in group:
                tx_id = t.get('transaction_id')
                if tx_id not in displayed_set:
                    displayed_set.add(tx_id)
                    display_order.append(t)
                    
        # Sort display by timestamp
        display_order.sort(key=lambda x: str(x.get('timestamp', '')))
        
        lines.append("  " + "-" * 88)
        lines.append(f"  {'Timestamp':<17} {'Txn ID':<13} {'Type':<10} {'Role':<10} {'Amount':>12} {'Curr':<4} {'Format':<12} {'Laundering'}")
        lines.append("  " + "-" * 88)
        for t in display_order:
            typ = "SYNTHETIC" if t.get('is_synthetic') else "REAL"
            amt = float(t.get('amount_paid', 0.0) or 0.0)
            curr = str(t.get('payment_currency') or 'USD')
            fmt = str(t.get('payment_format') or 'Payment')
            role = str(t.get('account_role') or '')
            isl = "YES (1)" if t.get('is_laundering') == 1 else "NO (0)"
            lines.append(f"  {t.get('timestamp', ''):<17} {t.get('transaction_id', ''):<13} {typ:<10} {role:<10} {amt:>12,.2f} {curr:<4} {fmt:<12} {isl}")
        if len(txns) > len(display_order):
            lines.append(f"  ... [+{len(txns) - len(display_order)} more transactions omitted from print preview; all {len(txns)} present in returned dictionary] ...")
    else:
        lines.append("  No transactions found.")
        
    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) > 1:
        target = sys.argv[1]
        res = get_account_history(target)
        print(format_account_history_report(res))
    else:
        scen_df = pd.read_csv(HR_DIR / "labeled_scenarios.csv")
        s01_acct = scen_df[scen_df['scenario_id'] == 'S01']['account_id'].iloc[0]
        l01_acct = scen_df[scen_df['scenario_id'] == 'L01']['account_id'].iloc[0]
        
        print(f"=== TESTING S01 (Account: {s01_acct}) ===")
        s01_hist = get_account_history(s01_acct)
        print(format_account_history_report(s01_hist))
        
        print("\n\n" + "#" * 80 + "\n\n")
        
        print(f"=== TESTING L01 (Account: {l01_acct}) ===")
        l01_hist = get_account_history(l01_acct)
        print(format_account_history_report(l01_hist))
