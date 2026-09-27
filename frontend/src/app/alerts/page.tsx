"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  AlertOctagon,
  Search,
  Filter,
  ArrowRight,
  Shield,
  RefreshCw,
} from "lucide-react";

import { api, TraceXApiClientError } from "@/lib/api";
import type { AlertSummary, RiskTier } from "@/types/api";
import { RiskTierBadge } from "@/components/common/RiskTierBadge";
import { TableSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState, EmptyState } from "@/components/common/ErrorState";
import { formatScore } from "@/lib/utils";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTier, setSelectedTier] = useState<RiskTier | "All">("Low");
  const [selectedScenarioType, setSelectedScenarioType] = useState<string>("All");

  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAlerts(
        selectedTier,
        selectedScenarioType !== "All" ? selectedScenarioType : undefined
      );
      setAlerts(data);
    } catch (err: unknown) {
      if (err instanceof TraceXApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to fetch alerts from backend");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [selectedTier, selectedScenarioType]);

  // Client-side text search
  const filteredAlerts = useMemo(() => {
    if (!searchQuery.trim()) return alerts;
    const query = searchQuery.toLowerCase().trim();
    return alerts.filter(
      (a) =>
        a.account_id.toLowerCase().includes(query) ||
        a.alert_id.toLowerCase().includes(query) ||
        a.scenario_id?.toLowerCase().includes(query) ||
        a.fired_rules?.some((r) => r.toLowerCase().includes(query))
    );
  }, [alerts, searchQuery]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-cyan-400 font-mono text-xs tracking-widest uppercase">
              OPERATIONS / TRIAGE
            </span>
            <span className="w-1 h-1 rounded-full bg-cyan-400" />
            <span className="text-slate-500 font-mono text-xs">ALERT INVENTORY</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-100 tracking-tight">
            Security & AML Alerts
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Prioritize and filter automated alerts flagged by the multi-signal detection pipeline.
          </p>
        </div>

        <button
          onClick={fetchAlerts}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-mono text-slate-300 transition-colors self-start md:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          <span>REFRESH QUEUE</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel rounded-xl p-4 border border-slate-800 flex flex-col md:flex-row items-center gap-4">
        {/* Search */}
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search account, alert, scenario, or fired rule..."
            className="w-full bg-slate-900/90 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-xs font-mono text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          {/* Min Tier */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500">Tier:</span>
            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value as RiskTier | "All")}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="Low" className="bg-slate-900">All (≥ Low)</option>
              <option value="Medium" className="bg-slate-900">≥ Medium</option>
              <option value="High" className="bg-slate-900">≥ High</option>
              <option value="Critical" className="bg-slate-900">Critical only</option>
            </select>
          </div>

          {/* Scenario Type */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono">
            <span className="text-slate-500">Type:</span>
            <select
              value={selectedScenarioType}
              onChange={(e) => setSelectedScenarioType(e.target.value)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-slate-900">All Scenarios</option>
              <option value="suspicious" className="bg-slate-900">Suspicious</option>
              <option value="legitimate" className="bg-slate-900">Legitimate</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Table Content */}
      {error ? (
        <ErrorState
          title="Could Not Fetch Alerts"
          message={error}
          onRetry={fetchAlerts}
        />
      ) : loading ? (
        <div className="glass-panel rounded-xl p-6 border border-slate-800">
          <TableSkeleton rows={8} />
        </div>
      ) : filteredAlerts.length === 0 ? (
        <EmptyState
          title="No Alerts Match Filters"
          message="Try loosening your risk tier or scenario type filters."
          actionText="Reset Filters"
          onAction={() => {
            setSelectedTier("Low");
            setSelectedScenarioType("All");
            setSearchQuery("");
          }}
        />
      ) : (
        <div className="glass-panel rounded-xl border border-slate-800 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono text-slate-300 font-semibold">
                Showing {filteredAlerts.length} Alerts
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-500">
              Ranked by Fusion Risk Score
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800/80 bg-slate-900/60 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                  <th className="py-3 px-5">Alert ID</th>
                  <th className="py-3 px-4">Account ID</th>
                  <th className="py-3 px-4">Scenario</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Risk Tier</th>
                  <th className="py-3 px-4">Risk Score</th>
                  <th className="py-3 px-4">ML Flags</th>
                  <th className="py-3 px-4">Triggered Rules</th>
                  <th className="py-3 px-5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 text-xs">
                {filteredAlerts.map((alert) => (
                  <tr
                    key={alert.alert_id}
                    className="hover:bg-slate-800/30 transition-colors group"
                  >
                    <td className="py-3.5 px-5 font-mono text-slate-300 font-medium">
                      <div className="flex items-center gap-1.5">
                        <Shield className="w-3.5 h-3.5 text-cyan-400" />
                        <span>{alert.alert_id}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-100">
                      {alert.account_id}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">
                      {alert.scenario_id || "—"}
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                          alert.scenario_type?.toLowerCase() === "suspicious"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-slate-800 text-slate-400 border border-slate-700/60"
                        }`}
                      >
                        {alert.scenario_type || "Unknown"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <RiskTierBadge tier={alert.risk_tier} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-100">
                      {formatScore(alert.risk_score)}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      <div className="flex items-center gap-1.5">
                        {alert.is_xgboost_flagged && (
                          <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px]">
                            XGB
                          </span>
                        )}
                        {alert.is_iforest_flagged && (
                          <span className="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[10px]">
                            IFOR
                          </span>
                        )}
                        {!alert.is_xgboost_flagged && !alert.is_iforest_flagged && (
                          <span className="text-slate-600">—</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 max-w-xs font-mono text-[11px] text-slate-300">
                      {alert.fired_rules && alert.fired_rules.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {alert.fired_rules.map((rule, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20"
                            >
                              {rule}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-600">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-5 text-right">
                      <Link
                        href={`/investigation/${alert.account_id}`}
                        className="inline-flex items-center gap-1 px-3 py-1 rounded bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 font-mono text-xs transition-colors"
                      >
                        <span>Investigate</span>
                        <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
