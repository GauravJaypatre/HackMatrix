"""
api.py — FastAPI Backend for HackMatrix Alert & Investigation Platform

Endpoints:
  - GET  /alerts                   : List all accounts with risk_tier >= Medium, sorted by risk_score descending
  - GET  /alerts/{account_id}      : Full explainable evidence object for one account
  - GET  /alerts/{account_id}/evidence : Just the evidence_subgraph + timeline portion
  - POST /cases                    : Create an investigation case record
  - POST /cases/{case_id}/assign   : Assign a case to a reviewer
  - GET  /cases/{case_id}/export   : Export case & full evidence object as downloadable JSON
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Path configuration
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR.parent
PROJECT_ROOT = DATA_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

try:
    from data.backend.evidence_schema import build_evidence_object
except ImportError:
    from backend.evidence_schema import build_evidence_object

try:
    from data.risk_fusion.fuse_signals import compute_scenario_risk_scores, fuse_account_risk
except ImportError:
    from risk_fusion.fuse_signals import compute_scenario_risk_scores, fuse_account_risk

# FastAPI Application
app = FastAPI(
    title="HackMatrix Financial Crime & Insider Risk Intelligence API",
    description="Investigation API linking employees, access rights, customers, and transactions with explainable, evidence-backed alerts.",
    version="1.0.0"
)

# Enable CORS for Member 4's Frontend Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory & File Storage for Cases
CASES_FILE = BACKEND_DIR / "cases_store.json"
CASES_DB: Dict[str, Dict[str, Any]] = {}


def _load_cases() -> None:
    """Load cases from JSON file if it exists."""
    global CASES_DB
    if CASES_FILE.exists():
        try:
            with open(CASES_FILE, "r", encoding="utf-8") as f:
                CASES_DB = json.load(f)
        except Exception:
            CASES_DB = {}


def _save_cases() -> None:
    """Persist cases to JSON file."""
    try:
        with open(CASES_FILE, "w", encoding="utf-8") as f:
            json.dump(CASES_DB, f, indent=2)
    except Exception:
        pass


_load_cases()


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class CreateCaseRequest(BaseModel):
    account_id: str = Field(..., description="Target account ID for the case")
    alert_id: Optional[str] = Field(None, description="Linked alert ID (e.g. ALT-800085BF0)")
    title: Optional[str] = Field(None, description="Short case title or summary")
    notes: Optional[str] = Field(None, description="Initial investigator notes")
    assigned_to: Optional[str] = Field(None, description="Investigator / reviewer name")
    priority: Optional[str] = Field("HIGH", description="Case priority (LOW, MEDIUM, HIGH, CRITICAL)")


class AssignCaseRequest(BaseModel):
    reviewer: str = Field(..., description="Name or ID of reviewer to assign")


# ─── Alert Endpoints ──────────────────────────────────────────────────────────

@app.get("/alerts", summary="List all high/medium risk alerts")
def get_alerts(
    min_tier: str = Query("Medium", description="Minimum risk tier (Low, Medium, High, Critical)"),
    scenario_type: Optional[str] = Query(None, description="Filter by scenario_type (suspicious/legitimate)")
) -> List[Dict[str, Any]]:
    """
    List all accounts with risk_tier >= min_tier (default: Medium),
    sorted by risk_score descending.
    """
    scores_path = DATA_DIR / "risk_fusion" / "scenario_risk_scores.csv"
    if not scores_path.exists():
        df = compute_scenario_risk_scores(scores_path)
    else:
        df = pd.read_csv(scores_path, dtype={"account_id": str})
        
    tier_order = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
    min_val = tier_order.get(min_tier.capitalize(), 1)
    
    # Filter by minimum tier
    df["tier_val"] = df["risk_tier"].map(lambda t: tier_order.get(t, 0))
    filtered = df[df["tier_val"] >= min_val].copy()
    
    if scenario_type:
        filtered = filtered[filtered["scenario_type"].str.lower() == scenario_type.lower()]
        
    # Sort by risk_score descending
    filtered = filtered.sort_values(by="risk_score", ascending=False)
    
    results = []
    for _, row in filtered.iterrows():
        fired_list = [r for r in str(row.get("fired_rules", "")).split(";") if r]
        results.append({
            "alert_id": f"ALT-{row['account_id']}",
            "account_id": str(row["account_id"]),
            "scenario_id": str(row.get("scenario_id", "")),
            "scenario_type": str(row.get("scenario_type", "")),
            "risk_score": float(row["risk_score"]),
            "risk_tier": str(row["risk_tier"]),
            "fired_rules": fired_list,
            "rule_score": float(row.get("rule_score", 0.0)),
            "xgb_probability": float(row.get("xgb_probability", 0.0)),
            "iforest_score": float(row.get("iforest_score", 0.0)),
            "graph_anomaly_score": float(row.get("graph_anomaly_score", 0.0)),
            "is_xgboost_flagged": bool(row.get("is_xgboost_flagged", False)),
            "is_iforest_flagged": bool(row.get("is_iforest_flagged", False))
        })
        
    return results


@app.get("/alerts/{account_id}", summary="Get full evidence object for an account")
def get_alert_detail(account_id: str, include_background: bool = False) -> Dict[str, Any]:
    """
    Returns the complete, evidence-backed alert object for one account,
    including graph intelligence, ML probability, fired rules, subgraph, and timeline.
    """
    acc_id = str(account_id).strip()
    try:
        evidence = build_evidence_object(acc_id, include_background_context=include_background)
        return evidence
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to generate evidence for account {acc_id}: {str(e)}")


@app.get("/alerts/{account_id}/evidence", summary="Get evidence subgraph and timeline only")
def get_alert_evidence_only(account_id: str) -> Dict[str, Any]:
    """
    Returns only the evidence_subgraph and timeline portion of the alert.
    Useful for lightweight graph rendering in frontend visualizations.
    """
    acc_id = str(account_id).strip()
    try:
        evidence = build_evidence_object(acc_id)
        return {
            "alert_id": evidence["alert_id"],
            "account_id": acc_id,
            "risk_tier": evidence["risk_tier"],
            "risk_score": evidence["risk_score"],
            "evidence_subgraph": evidence["evidence_subgraph"],
            "timeline": evidence["timeline"],
            "explanation": evidence["explanation"]
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch evidence for account {acc_id}: {str(e)}")


# ─── Case Management Endpoints ────────────────────────────────────────────────

@app.post("/cases", status_code=201, summary="Create an investigation case")
def create_case(req: CreateCaseRequest) -> Dict[str, Any]:
    """
    Create a new case record for an account or alert.
    """
    acc_id = str(req.account_id).strip()
    case_count = len(CASES_DB) + 1
    case_id = f"CASE-{case_count:04d}"
    
    # Check if alert exists or compute its tier
    alert_id = req.alert_id or f"ALT-{acc_id}"
    
    try:
        evidence = build_evidence_object(acc_id)
        risk_tier = evidence.get("risk_tier", "Unknown")
        risk_score = evidence.get("risk_score", 0.0)
    except Exception:
        risk_tier = "Unknown"
        risk_score = 0.0
        
    now = datetime.now(timezone.utc).isoformat()
    
    case_record = {
        "case_id": case_id,
        "account_id": acc_id,
        "alert_id": alert_id,
        "title": req.title or f"Investigation into Account {acc_id} ({risk_tier} Risk)",
        "notes": req.notes or "Initial case created from detection alert.",
        "assigned_to": req.assigned_to or "Unassigned",
        "priority": req.priority or ("CRITICAL" if risk_tier == "Critical" else "HIGH"),
        "status": "OPEN",
        "risk_tier": risk_tier,
        "risk_score": risk_score,
        "created_at": now,
        "updated_at": now
    }
    
    CASES_DB[case_id] = case_record
    _save_cases()
    return case_record


@app.get("/cases", summary="List all investigation cases")
def list_cases() -> List[Dict[str, Any]]:
    """Return all cases currently registered."""
    return list(CASES_DB.values())


@app.get("/cases/{case_id}", summary="Get case details by ID")
def get_case(case_id: str) -> Dict[str, Any]:
    """Return details of a specific case."""
    cid = str(case_id).strip().upper()
    if cid not in CASES_DB:
        raise HTTPException(status_code=404, detail=f"Case {cid} not found.")
    return CASES_DB[cid]


@app.post("/cases/{case_id}/assign", summary="Assign case to a reviewer")
def assign_case(case_id: str, req: AssignCaseRequest) -> Dict[str, Any]:
    """
    Assign a case to a specific reviewer or investigator name.
    """
    cid = str(case_id).strip().upper()
    if cid not in CASES_DB:
        raise HTTPException(status_code=404, detail=f"Case {cid} not found.")
        
    CASES_DB[cid]["assigned_to"] = req.reviewer.strip()
    CASES_DB[cid]["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_cases()
    return CASES_DB[cid]


@app.get("/cases/{case_id}/export", summary="Export case and full evidence as JSON")
def export_case(case_id: str) -> Response:
    """
    Return the full case record bundled with the complete evidence object
    as a downloadable JSON file.
    """
    cid = str(case_id).strip().upper()
    if cid not in CASES_DB:
        raise HTTPException(status_code=404, detail=f"Case {cid} not found.")
        
    case = CASES_DB[cid]
    acc_id = case["account_id"]
    
    try:
        evidence = build_evidence_object(acc_id)
    except Exception as e:
        evidence = {"error": f"Failed to build evidence: {str(e)}"}
        
    export_payload = {
        "export_metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "system": "HackMatrix Financial Crime Intelligence Platform",
            "version": "1.0.0"
        },
        "case": case,
        "evidence_package": evidence
    }
    
    content = json.dumps(export_payload, indent=2, ensure_ascii=False)
    filename = f"{cid}_{acc_id}_evidence.json"
    
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ─── Self-Test Runner ─────────────────────────────────────────────────────────

def run_api_self_tests() -> None:
    """Run programmatic tests against all endpoints using TestClient."""
    from starlette.testclient import TestClient
    client = TestClient(app)
    
    print("=" * 100)
    print("RUNNING FASTAPI ENDPOINTS VERIFICATION")
    print("=" * 100)
    
    # 1. Test GET /alerts
    print("\n[TEST 1] GET /alerts")
    r1 = client.get("/alerts")
    assert r1.status_code == 200, f"GET /alerts failed: {r1.status_code}"
    alerts = r1.json()
    print(f"Total alerts returned (risk_tier >= Medium): {len(alerts)}")
    assert len(alerts) > 0, "Expected alerts returned"
    
    # Verify sorting
    scores = [a["risk_score"] for a in alerts]
    assert scores == sorted(scores, reverse=True), "Alerts must be sorted descending by risk_score"
    print("Top 3 alerts from /alerts:")
    for a in alerts[:3]:
        print(f"  - {a['alert_id']}: Score={a['risk_score']:.4f} ({a['risk_tier']}), Rules={a['fired_rules']}")
        
    # 2. Test GET /alerts/800085BF0 (S19)
    print("\n[TEST 2] GET /alerts/800085BF0 (S19 Circular Transfer)")
    r2 = client.get("/alerts/800085BF0")
    assert r2.status_code == 200, f"GET /alerts/800085BF0 failed: {r2.status_code}"
    s19_data = r2.json()
    assert s19_data["alert_id"] == "ALT-800085BF0"
    assert s19_data["risk_tier"] in ["High", "Critical"]
    print(f"S19 Alert: Tier={s19_data['risk_tier']}, Score={s19_data['risk_score']}")
    print(f"Explanation: {s19_data['explanation'][:160]}...")
    
    # 3. Test GET /alerts/800085BF0/evidence
    print("\n[TEST 3] GET /alerts/800085BF0/evidence")
    r3 = client.get("/alerts/800085BF0/evidence")
    assert r3.status_code == 200, f"GET /alerts/800085BF0/evidence failed: {r3.status_code}"
    ev_data = r3.json()
    assert "evidence_subgraph" in ev_data and "timeline" in ev_data
    print(f"Subgraph nodes: {len(ev_data['evidence_subgraph']['nodes'])}, edges: {len(ev_data['evidence_subgraph']['edges'])}, timeline events: {len(ev_data['timeline'])}")
    
    # 4. Test POST /cases
    print("\n[TEST 4] POST /cases")
    case_payload = {
        "account_id": "800085BF0",
        "title": "Suspected circular transfer and unauthorized privilege change",
        "notes": "Flagged by automated multi-signal risk fusion engine for urgent SAR review.",
        "assigned_to": "Sarah Connor",
        "priority": "CRITICAL"
    }
    r4 = client.post("/cases", json=case_payload)
    assert r4.status_code == 201, f"POST /cases failed: {r4.status_code}"
    case_obj = r4.json()
    case_id = case_obj["case_id"]
    print(f"Created case: {case_id} assigned to '{case_obj['assigned_to']}' with priority '{case_obj['priority']}'")
    
    # 5. Test POST /cases/{case_id}/assign
    print(f"\n[TEST 5] POST /cases/{case_id}/assign")
    r5 = client.post(f"/cases/{case_id}/assign", json={"reviewer": "Alex Morgan (Senior AML Lead)"})
    assert r5.status_code == 200, f"POST /cases/{case_id}/assign failed: {r5.status_code}"
    assigned_obj = r5.json()
    assert assigned_obj["assigned_to"] == "Alex Morgan (Senior AML Lead)"
    print(f"Case {case_id} successfully reassigned to: {assigned_obj['assigned_to']}")
    
    # 6. Test GET /cases/{case_id}/export
    print(f"\n[TEST 6] GET /cases/{case_id}/export")
    r6 = client.get(f"/cases/{case_id}/export")
    assert r6.status_code == 200, f"GET /cases/{case_id}/export failed: {r6.status_code}"
    assert "attachment" in r6.headers.get("Content-Disposition", "")
    exported_json = r6.json()
    assert "case" in exported_json and "evidence_package" in exported_json
    print(f"Successfully exported case evidence package ({len(r6.content)} bytes). Filename: {r6.headers['Content-Disposition']}")
    
    print("\n" + "=" * 100)
    print("ALL API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY ✅")
    print("=" * 100)


if __name__ == "__main__":
    run_api_self_tests()
