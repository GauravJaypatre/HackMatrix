"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  UserCheck,
  Network,
  Briefcase,
  Layers,
  CheckCircle2,
  FileText,
  Activity,
  Zap,
  ExternalLink,
} from "lucide-react";

import { api, TraceXApiClientError } from "@/lib/api";
import type { AlertDetail, CreateCaseRequest } from "@/types/api";
import { RiskTierBadge } from "@/components/common/RiskTierBadge";
import { ScoreGauge } from "@/components/common/ScoreGauge";
import { SignalCard } from "@/components/common/SignalCard";
import { ErrorState } from "@/components/common/ErrorState";
import { formatScore, formatPercent } from "@/lib/utils";

interface PageProps {
  params: Promise<{ accountId: string }>;
}

export default function InvestigationPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const accountId = resolvedParams.accountId?.trim().toUpperCase();

  const [detail, setDetail] = useState<AlertDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Case creation form state
  const [showCaseModal, setShowCaseModal] = useState(false);
  const [caseTitle, setCaseTitle] = useState("");
  const [casePriority, setCasePriority] = useState<"CRITICAL" | "HIGH" | "MEDIUM" | "LOW">("CRITICAL");
  const [caseAssignee, setCaseAssignee] = useState("Sarah Connor (Lead AML)");
  const [caseNotes, setCaseNotes] = useState("Automated investigation initiated via Trace-X multi-signal console.");
  const [creatingCase, setCreatingCase] = useState(false);
  const [caseSuccess, setCaseSuccess] = useState<string | null>(null);

  // Active section tab
  const [activeTab, setActiveTab] = useState<"overview" | "rules" | "models" | "graph" | "timeline">("overview");

  const fetchAlertDetail = async () => {
    if (!accountId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAlert(accountId, true);
      setDetail(data);
      setCaseTitle(`Investigation into Account ${accountId} (${data.risk_tier} Risk)`);
      if (data.risk_tier === "Critical") setCasePriority("CRITICAL");
      else if (data.risk_tier === "High") setCasePriority("HIGH");
      else setCasePriority("MEDIUM");
    } catch (err: unknown) {
      if (err instanceof TraceXApiClientError) {
        setError(err.message);
      } else {
        setError(`Failed to retrieve evidence package for account ${accountId}`);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlertDetail();
  }, [accountId]);

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setCreatingCase(true);
    setCaseSuccess(null);
    try {
      const payload: CreateCaseRequest = {
        account_id: accountId,
        alert_id: detail.alert_id,
        title: caseTitle,
        priority: casePriority,
        assigned_to: caseAssignee,
        notes: caseNotes,
      };
      const created = await api.createCase(payload);
      setCaseSuccess(created.case_id);
      setTimeout(() => {
        setShowCaseModal(false);
      }, 2000);
    } catch (err: unknown) {
      alert(`Failed to create case: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setCreatingCase(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-slate-800/80 rounded w-1/3" />
        <div className="h-44 bg-slate-900/60 rounded-xl border border-slate-800" />
        <div className="grid grid-cols-4 gap-4">
          <div className="h-32 bg-slate-900/60 rounded-xl" />
          <div className="h-32 bg-slate-900/60 rounded-xl" />
          <div className="h-32 bg-slate-900/60 rounded-xl" />
          <div className="h-32 bg-slate-900/60 rounded-xl" />
        </div>
        <div className="h-64 bg-slate-900/60 rounded-xl" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="py-12">
        <ErrorState
          title={`Investigation Target Not Found: ${accountId}`}
          message={error || "Account could not be found or has no active alert data."}
          onRetry={fetchAlertDetail}
        />
      </div>
    );
  }

  const { signals, evidence_subgraph, timeline } = detail;
  const ruleSig = signals?.rule_engine;
  const xgbSig = signals?.ml_model?.xgboost;
  const iforestSig = signals?.ml_model?.isolation_forest;
  const graphSig = signals?.graph_intelligence;

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Link href="/alerts" className="hover:text-cyan-400 transition-colors">
            ALERTS
          </Link>
          <span>/</span>
          <span className="text-cyan-400 font-bold">{detail.alert_id}</span>
          <span>/</span>
          <span className="text-slate-200">TARGET: {accountId}</span>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/graph?account=${accountId}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-mono text-cyan-300 transition-colors"
          >
            <Network className="w-3.5 h-3.5 text-cyan-400" />
            <span>OPEN NETWORK GRAPH</span>
          </Link>

          <button
            onClick={() => setShowCaseModal(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-mono font-bold text-xs shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all"
          >
            <Briefcase className="w-3.5 h-3.5" />
            <span>CREATE CASE</span>
          </button>
        </div>
      </div>

      {/* Hero Banner: Target Score, Tier, and Entities */}
      <div className="glass-panel-glow rounded-2xl p-6 md:p-8 border border-cyan-500/20 relative overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left Column: Target Identifiers */}
          <div className="lg:col-span-8 space-y-4">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                {detail.alert_id}
              </span>
              <RiskTierBadge tier={detail.risk_tier} size="md" />
              {detail.employee_id && (
                <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-300 border border-rose-500/30 flex items-center gap-1.5">
                  <UserCheck className="w-3 h-3 text-rose-400" />
                  INSIDER: {detail.employee_id}
                </span>
              )}
            </div>

            <div>
              <h1 className="text-3xl md:text-4xl font-extrabold font-mono tracking-tight text-white flex items-center gap-3">
                {accountId}
              </h1>
              <p className="text-sm text-slate-300 mt-1 max-w-2xl leading-relaxed">
                {detail.explanation}
              </p>
            </div>

            {/* Linked Entity Badges */}
            <div className="pt-2 flex flex-wrap items-center gap-3 text-xs font-mono text-slate-400 border-t border-slate-800/80">
              <div className="flex items-center gap-1.5">
                <span className="text-slate-500">Chain Accounts ({detail.account_ids?.length || 1}):</span>
                <span className="text-cyan-400 font-semibold">
                  {detail.account_ids?.join(", ") || accountId}
                </span>
              </div>
              <span>•</span>
              <div>
                <span className="text-slate-500">Evidence Nodes:</span>{" "}
                <span className="text-slate-200">{evidence_subgraph?.nodes?.length || 0}</span>
              </div>
              <span>•</span>
              <div>
                <span className="text-slate-500">Timeline Events:</span>{" "}
                <span className="text-slate-200">{timeline?.length || 0}</span>
              </div>
            </div>
          </div>

          {/* Right Column: Animated Score Gauge */}
          <div className="lg:col-span-4 flex flex-col items-center justify-center border-t lg:border-t-0 lg:border-l border-slate-800/80 pt-6 lg:pt-0 lg:pl-6">
            <ScoreGauge
              score={detail.risk_score}
              tier={detail.risk_tier}
              size={190}
              strokeWidth={13}
              label="Composite Risk"
              subtitle="Fusion Score"
            />
          </div>
        </div>
      </div>

      {/* 4 Multi-Signal Pillar Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono text-cyan-400 uppercase tracking-widest font-semibold">
              MULTI-SIGNAL FUSION DECOMPOSITION
            </span>
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Formula: 0.16·Rules + 0.50·XGB + 0.14·IForest + 0.20·Graph
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Signal 1: Rule Engine */}
          <SignalCard
            title="Rule Engine"
            subtitle="Deterministic Compliance"
            value={ruleSig?.triggered ? `${ruleSig.rule_count} Fired` : "Clear"}
            status={ruleSig?.triggered ? "triggered" : "clear"}
            icon={ShieldAlert}
            weight="16% WEIGHT"
            detail={ruleSig?.fired_rules?.join(", ") || "No AML/Insider thresholds breached"}
          />

          {/* Signal 2: XGBoost Classifier */}
          <SignalCard
            title="XGBoost Model"
            subtitle="Supervised ML"
            value={formatPercent(xgbSig?.probability)}
            status={xgbSig?.is_suspicious ? "triggered" : "clear"}
            icon={Activity}
            weight="50% WEIGHT"
            detail={`Threshold: ${xgbSig?.decision_threshold ?? 0.50} | Probability: ${formatScore(xgbSig?.probability)}`}
          />

          {/* Signal 3: Isolation Forest */}
          <SignalCard
            title="Isolation Forest"
            subtitle="Unsupervised Outlier"
            value={formatScore(iforestSig?.anomaly_score)}
            status={iforestSig?.is_anomaly ? "warning" : "clear"}
            icon={Layers}
            weight="14% WEIGHT"
            detail={iforestSig?.interpretation || (iforestSig?.is_anomaly ? "Outlier detected in multi-feature transaction space" : "Normal transaction behavior")}
          />

          {/* Signal 4: Graph Intelligence */}
          <SignalCard
            title="Graph Intelligence"
            subtitle="Topology & Cycles"
            value={formatScore(graphSig?.graph_anomaly_score)}
            status={(graphSig?.graph_anomaly_score || 0) > 0.4 ? "triggered" : (graphSig?.graph_anomaly_score || 0) > 0.15 ? "warning" : "clear"}
            icon={Network}
            weight="20% WEIGHT"
            detail={graphSig?.contributing_factors || "No topological anomalies identified"}
          />
        </div>
      </div>

      {/* Tabs navigation for deep-dive */}
      <div className="border-b border-slate-800 flex items-center gap-2 overflow-x-auto pb-1 text-xs font-mono">
        {[
          { id: "overview", label: "Overview & Narrative" },
          { id: "rules", label: `Rule Engine (${ruleSig?.details?.length || 0})` },
          { id: "models", label: "ML & SHAP Explainability" },
          { id: "graph", label: "Graph & Topology" },
          { id: "timeline", label: `Evidence Timeline (${timeline?.length || 0})` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`px-4 py-2.5 rounded-t-lg font-medium transition-all ${
              activeTab === tab.id
                ? "bg-slate-900 border-t-2 border-cyan-400 text-cyan-300 font-bold border-x border-slate-800"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Overview & Narrative */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Analyst Narrative */}
            <div className="lg:col-span-7 glass-panel rounded-xl p-6 border border-slate-800">
              <div className="flex items-center justify-between mb-4">
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                  CASE EXPLAINABILITY
                </span>
                <span className="text-xs font-mono text-slate-500">Auto-Generated Narrative</span>
              </div>
              <h3 className="text-base font-bold text-slate-100 mb-3">
                Executive Synthesis
              </h3>
              <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800/80 font-mono text-xs text-slate-300 leading-relaxed space-y-3">
                <p>{detail.explanation}</p>
                {graphSig?.contributing_factors && (
                  <p className="text-cyan-400/90 pt-2 border-t border-slate-800">
                    <strong className="text-cyan-300">Graph Factors:</strong> {graphSig.contributing_factors}
                  </p>
                )}
              </div>

              {/* Action shortcuts */}
              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href={`/graph?account=${accountId}`}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 font-mono text-xs transition-colors"
                >
                  <Network className="w-3.5 h-3.5" />
                  <span>Inspect React Flow Network</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
                <Link
                  href={`/evidence?account=${accountId}`}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 font-mono text-xs transition-colors"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>View Timeline In Evidence Vault</span>
                </Link>
              </div>
            </div>

            {/* Quick Subgraph Snapshot */}
            <div className="lg:col-span-5 glass-panel rounded-xl p-6 border border-slate-800">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                  LOCAL TOPOLOGY
                </span>
                <span className="text-xs font-mono text-slate-500">
                  {evidence_subgraph?.nodes?.length || 0} Nodes • {evidence_subgraph?.edges?.length || 0} Edges
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-100 mb-3">
                Connected Entity Roster
              </h3>

              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {evidence_subgraph?.nodes?.map((node) => (
                  <div
                    key={node.id}
                    className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800/80 flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase ${
                          node.type === "Account"
                            ? "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                            : node.type === "Customer"
                            ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                            : node.type === "Employee"
                            ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                            : "bg-purple-500/15 text-purple-400 border border-purple-500/30"
                        }`}
                      >
                        {node.type}
                      </span>
                      <span className="font-mono text-slate-200 font-medium truncate max-w-[200px]">
                        {node.label || node.id}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-slate-500">
                      {node.id}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Rule Engine */}
      {activeTab === "rules" && (
        <div className="glass-panel rounded-xl p-6 border border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                RULE SYSTEM SIGNALS
              </span>
              <h3 className="text-lg font-bold text-slate-100 mt-0.5">
                Deterministic AML & Insider Rule Evidence
              </h3>
            </div>
            <div className="text-right">
              <span className="text-xs font-mono text-slate-400">Score Impact: </span>
              <span className="text-sm font-mono font-bold text-cyan-300">
                {formatScore(ruleSig?.rule_score)}
              </span>
            </div>
          </div>

          {ruleSig?.details && ruleSig.details.length > 0 ? (
            <div className="space-y-4">
              {ruleSig.details.map((rule, idx) => (
                <div
                  key={idx}
                  className="p-5 rounded-xl bg-slate-900/90 border border-rose-500/30 relative overflow-hidden"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 font-mono text-xs font-bold">
                        {rule.rule_id}
                      </span>
                      <h4 className="text-sm font-bold text-slate-100">
                        {rule.rule_name}
                      </h4>
                    </div>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 uppercase">
                      Category: {rule.detection_category}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-mono">
                    {rule.explanation}
                  </p>
                  <div className="mt-3 text-[11px] font-mono text-slate-500">
                    Evidence events bound: {rule.evidence_count}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 font-mono text-xs">
              No deterministic rules triggered for this account.
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Machine Learning & SHAP */}
      {activeTab === "models" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* XGBoost Details & SHAP Bar Impact */}
            <div className="glass-panel rounded-xl p-6 border border-slate-800">
              <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                <div>
                  <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                    SUPERVISED CLASSIFIER
                  </span>
                  <h3 className="text-base font-bold text-slate-100 mt-0.5">
                    XGBoost Model & SHAP Explanations
                  </h3>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono text-slate-400">Probability: </span>
                  <span className="text-sm font-mono font-bold text-cyan-300">
                    {formatPercent(xgbSig?.probability)}
                  </span>
                </div>
              </div>

              <div className="space-y-3 mb-6">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-slate-400">Classification Status:</span>
                  <span className={xgbSig?.is_suspicious ? "text-rose-400 font-bold" : "text-emerald-400"}>
                    {xgbSig?.is_suspicious ? "FLAGGED SUSPICIOUS" : "NORMAL"}
                  </span>
                </div>
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-slate-400">Decision Threshold:</span>
                  <span className="text-slate-200">{xgbSig?.decision_threshold ?? 0.50}</span>
                </div>
              </div>

              {/* SHAP Feature Contribution Bars */}
              <h4 className="text-xs font-mono uppercase text-slate-400 tracking-wider mb-3">
                Top Contributing SHAP Features
              </h4>
              <div className="space-y-3">
                {xgbSig?.top_shap_features && xgbSig.top_shap_features.length > 0 ? (
                  xgbSig.top_shap_features.map((feat, idx) => {
                    const isPositive = feat.shap_value > 0;
                    return (
                      <div key={idx} className="p-3 rounded-lg bg-slate-900/80 border border-slate-800/80">
                        <div className="flex justify-between items-center text-xs font-mono mb-1.5">
                          <span className="text-slate-200 font-medium">{feat.feature}</span>
                          <span className={isPositive ? "text-rose-400 font-bold" : "text-emerald-400"}>
                            {isPositive ? "+" : ""}{formatScore(feat.shap_value)}
                          </span>
                        </div>
                        {/* Bar */}
                        <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              isPositive ? "bg-rose-500" : "bg-emerald-500"
                            }`}
                            style={{ width: `${Math.min(100, Math.abs(feat.shap_value) * 100)}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
                          <span>Impact: {feat.impact}</span>
                          {feat.feature_value !== null && feat.feature_value !== undefined && (
                            <span>Value: {String(feat.feature_value)}</span>
                          )}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-xs font-mono text-slate-500">No SHAP breakdown available.</p>
                )}
              </div>
            </div>

            {/* Isolation Forest Details */}
            <div className="glass-panel rounded-xl p-6 border border-slate-800 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                  <div>
                    <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                      UNSUPERVISED ANOMALY
                    </span>
                    <h3 className="text-base font-bold text-slate-100 mt-0.5">
                      Isolation Forest Outlier Detection
                    </h3>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono text-slate-400">Score: </span>
                    <span className="text-sm font-mono font-bold text-cyan-300">
                      {formatScore(iforestSig?.anomaly_score)}
                    </span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3 font-mono text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Outlier Status:</span>
                    <span className={iforestSig?.is_anomaly ? "text-amber-400 font-bold" : "text-slate-400"}>
                      {iforestSig?.is_anomaly ? "ANOMALOUS OUTLIER" : "WITHIN NORMAL RANGE"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Anomaly Threshold:</span>
                    <span className="text-slate-200">{iforestSig?.threshold ?? 0.60}</span>
                  </div>
                  <p className="text-slate-400 pt-2 border-t border-slate-800 leading-relaxed">
                    {iforestSig?.interpretation ||
                      "Isolation Forest isolates instances by randomly selecting a feature and split value. High scores indicate fewer splits were required to isolate this account's transaction profile."}
                  </p>
                </div>
              </div>

              <div className="mt-6 p-4 rounded-xl bg-cyan-950/20 border border-cyan-500/20">
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider block mb-1">
                  Engine Calibration Note
                </span>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Both ML models are trained on corrected un-leaked features (generalizing LOSO-CV) and unified synthetic + real ledger transactions.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Graph & Topology */}
      {activeTab === "graph" && (
        <div className="glass-panel rounded-xl p-6 border border-slate-800 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                TOPOLOGICAL METRICS
              </span>
              <h3 className="text-lg font-bold text-slate-100 mt-0.5">
                Structural Graph Features & Centrality
              </h3>
            </div>

            <Link
              href={`/graph?account=${accountId}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 font-mono text-xs transition-colors self-start sm:self-auto"
            >
              <Network className="w-3.5 h-3.5" />
              <span>Full Interactive React Flow</span>
            </Link>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: "Cycle Member", value: graphSig?.structural_metrics?.is_on_any_cycle ? "YES" : "NO", highlight: graphSig?.structural_metrics?.is_on_any_cycle },
              { label: "Degree", value: graphSig?.structural_metrics?.degree ?? 0 },
              { label: "In Degree", value: graphSig?.structural_metrics?.in_degree ?? 0 },
              { label: "Out Degree", value: graphSig?.structural_metrics?.out_degree ?? 0 },
              { label: "Betweenness", value: formatScore(graphSig?.structural_metrics?.betweenness_centrality) },
              { label: "Clustering Coeff", value: formatScore(graphSig?.structural_metrics?.clustering_coefficient) },
              { label: "DBSCAN Cluster", value: graphSig?.clustering_metrics?.cluster_label !== undefined ? (graphSig.clustering_metrics.cluster_label === -1 ? "Noise" : graphSig.clustering_metrics.cluster_label) : "Noise" },
              { label: "Cluster Outlier", value: graphSig?.clustering_metrics?.is_outlier ? "TRUE" : "FALSE" },
              { label: "Cluster Size", value: graphSig?.clustering_metrics?.cluster_size ?? "N/A" },
              { label: "Insider Links", value: graphSig?.structural_metrics?.num_connected_employees ?? 0, highlight: (graphSig?.structural_metrics?.num_connected_employees || 0) > 0 },
              { label: "Composite Graph Score", value: formatScore(graphSig?.graph_anomaly_score), highlight: (graphSig?.graph_anomaly_score || 0) > 0.4 },
            ].map((m, idx) => (
              <div key={idx} className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
                  {m.label}
                </span>
                <span className={`text-sm font-mono font-bold mt-1 block ${m.highlight ? "text-rose-400" : "text-slate-200"}`}>
                  {String(m.value)}
                </span>
              </div>
            ))}
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 font-mono text-xs text-slate-300">
            <span className="text-cyan-400 font-semibold uppercase block mb-1">
              Topological Contributing Factors:
            </span>
            <p>{graphSig?.contributing_factors || "No topological factors triggered."}</p>
          </div>
        </div>
      )}

      {/* Tab 5: Evidence Timeline */}
      {activeTab === "timeline" && (
        <div className="glass-panel rounded-xl p-6 border border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                CHRONOLOGICAL TRAIL
              </span>
              <h3 className="text-lg font-bold text-slate-100 mt-0.5">
                Integrated Evidence Timeline
              </h3>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {timeline?.length || 0} Chronological Events
            </span>
          </div>

          {timeline && timeline.length > 0 ? (
            <div className="space-y-4 relative before:absolute before:inset-0 before:left-4 before:w-0.5 before:bg-slate-800">
              {timeline.map((event, idx) => (
                <div key={idx} className="relative pl-10">
                  {/* Timeline Dot */}
                  <div className="absolute left-2.5 top-1.5 w-3.5 h-3.5 rounded-full bg-slate-900 border-2 border-cyan-400 -translate-x-1/2 shadow-[0_0_8px_rgba(6,182,212,0.6)]" />

                  <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800/80 hover:border-slate-700 transition-colors">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                      <span className="font-mono text-xs font-bold text-cyan-300">
                        {event.timestamp}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase ${
                          event.event_type === "access_event"
                            ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                            : "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                        }`}
                      >
                        {event.event_type}
                      </span>
                    </div>

                    <p className="text-xs text-slate-200 font-medium mb-2">
                      {event.summary}
                    </p>

                    {event.details && (
                      <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800/60 font-mono text-[11px] text-slate-400 space-y-1">
                        {Object.entries(event.details).map(([k, v]) => (
                          <div key={k} className="flex justify-between">
                            <span className="text-slate-500">{k}:</span>
                            <span className="text-slate-300">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 font-mono text-xs">
              No timeline events recorded for this account.
            </div>
          )}
        </div>
      )}

      {/* Case Creation Modal */}
      {showCaseModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="glass-panel-glow bg-[#0b1220] border border-cyan-500/30 rounded-2xl p-6 md:p-8 max-w-lg w-full shadow-2xl relative">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-cyan-400" />
                <h3 className="text-lg font-bold text-slate-100">
                  Open Investigation Case
                </h3>
              </div>
              <button
                onClick={() => setShowCaseModal(false)}
                className="text-slate-400 hover:text-slate-200 text-xs font-mono"
              >
                ✕ CLOSE
              </button>
            </div>

            {caseSuccess ? (
              <div className="py-8 text-center space-y-3">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto animate-bounce" />
                <h4 className="text-base font-bold text-slate-100">
                  Case Created Successfully
                </h4>
                <p className="font-mono text-sm text-cyan-300">
                  Case ID: {caseSuccess}
                </p>
                <div className="pt-2">
                  <Link
                    href="/cases"
                    className="text-xs font-mono text-cyan-400 hover:underline"
                  >
                    View in Cases Desk →
                  </Link>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreateCase} className="space-y-4">
                <div>
                  <label className="text-xs font-mono text-slate-400 block mb-1">
                    Target Account
                  </label>
                  <input
                    type="text"
                    value={accountId}
                    disabled
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-400 cursor-not-allowed"
                  />
                </div>

                <div>
                  <label className="text-xs font-mono text-slate-300 block mb-1">
                    Case Title
                  </label>
                  <input
                    type="text"
                    required
                    value={caseTitle}
                    onChange={(e) => setCaseTitle(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-mono text-slate-300 block mb-1">
                      Priority
                    </label>
                    <select
                      value={casePriority}
                      onChange={(e) => setCasePriority(e.target.value as typeof casePriority)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
                    >
                      <option value="CRITICAL">CRITICAL</option>
                      <option value="HIGH">HIGH</option>
                      <option value="MEDIUM">MEDIUM</option>
                      <option value="LOW">LOW</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-mono text-slate-300 block mb-1">
                      Assigned Reviewer
                    </label>
                    <input
                      type="text"
                      value={caseAssignee}
                      onChange={(e) => setCaseAssignee(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-mono text-slate-300 block mb-1">
                    Investigator Notes
                  </label>
                  <textarea
                    rows={3}
                    value={caseNotes}
                    onChange={(e) => setCaseNotes(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setShowCaseModal(false)}
                    className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creatingCase}
                    className="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-mono font-bold text-xs shadow-lg transition-all"
                  >
                    {creatingCase ? "Registering Case..." : "Create Case Record"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
