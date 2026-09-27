"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ShieldAlert,
  AlertTriangle,
  Flame,
  Search,
  ArrowRight,
  TrendingUp,
  Activity,
  Layers,
  Sparkles,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

import { api, TraceXApiClientError } from "@/lib/api";
import type { AlertSummary } from "@/types/api";
import { RiskTierBadge } from "@/components/common/RiskTierBadge";
import { CardSkeleton, TableSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { DEFAULT_ACCOUNT, RISK_COLORS, formatScore } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [targetAccountInput, setTargetAccountInput] = useState(DEFAULT_ACCOUNT);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAlerts("Low");
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
    fetchDashboardData();
  }, []);

  // Compute metrics
  const totalAlerts = alerts.length;
  const criticalCount = alerts.filter((a) => a.risk_tier === "Critical").length;
  const highCount = alerts.filter((a) => a.risk_tier === "High").length;
  const suspiciousCount = alerts.filter((a) => a.scenario_type?.toLowerCase() === "suspicious").length;

  // Compute distribution for chart
  const tierCounts: Record<string, number> = {
    Critical: criticalCount,
    High: highCount,
    Medium: alerts.filter((a) => a.risk_tier === "Medium").length,
    Low: alerts.filter((a) => a.risk_tier === "Low").length,
  };

  const chartData = [
    { tier: "Critical", count: tierCounts.Critical, fill: RISK_COLORS.Critical.hex },
    { tier: "High", count: tierCounts.High, fill: RISK_COLORS.High.hex },
    { tier: "Medium", count: tierCounts.Medium, fill: RISK_COLORS.Medium.hex },
    { tier: "Low", count: tierCounts.Low, fill: RISK_COLORS.Low.hex },
  ];

  // Highest risk accounts (top 8)
  const topRiskAccounts = [...alerts]
    .sort((a, b) => b.risk_score - a.risk_score)
    .slice(0, 8);

  const handleLaunchInvestigation = (e: React.FormEvent) => {
    e.preventDefault();
    if (targetAccountInput.trim()) {
      router.push(`/investigation/${targetAccountInput.trim().toUpperCase()}`);
    }
  };

  if (error) {
    return (
      <div className="py-12">
        <ErrorState
          title="Investigation Desk Offline"
          message={error}
          onRetry={fetchDashboardData}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-cyan-400 font-mono text-xs tracking-widest uppercase">
              OPERATIONS / OVERVIEW
            </span>
            <span className="w-1 h-1 rounded-full bg-cyan-400" />
            <span className="text-slate-500 font-mono text-xs">TRIAGE COMMAND</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-100 tracking-tight">
            Financial Crime Investigation Desk
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Multi-signal risk fusion integrating structural graph intelligence, XGBoost classification, and deterministic rules.
          </p>
        </div>

        {/* Live Status Pill */}
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono self-start md:self-auto">
          <Activity className="w-4 h-4 text-cyan-400" />
          <span className="text-slate-400">Fusion Model:</span>
          <span className="text-cyan-300 font-semibold">Active (4 Signals)</span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          <>
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </>
        ) : (
          <>
            {/* Metric 1 */}
            <div className="glass-panel rounded-xl p-5 border border-slate-800 relative overflow-hidden group hover:border-slate-700 transition-colors">
              <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
                <span>Open Alerts</span>
                <Layers className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-3xl font-extrabold font-mono text-slate-100 tracking-tight">
                {totalAlerts}
              </div>
              <div className="text-xs text-slate-500 mt-1 font-mono">
                Across all risk categories
              </div>
            </div>

            {/* Metric 2 */}
            <div className="glass-panel rounded-xl p-5 border border-rose-500/30 relative overflow-hidden group hover:border-rose-500/50 shadow-[0_0_15px_rgba(244,63,94,0.08)] transition-all">
              <div className="flex items-center justify-between text-rose-400 text-xs font-medium mb-2">
                <span>Critical Risk</span>
                <Flame className="w-4 h-4 text-rose-400 animate-pulse" />
              </div>
              <div className="text-3xl font-extrabold font-mono text-rose-400 tracking-tight">
                {criticalCount}
              </div>
              <div className="text-xs text-rose-500/70 mt-1 font-mono">
                Score ≥ 0.75 (Immediate SAR review)
              </div>
            </div>

            {/* Metric 3 */}
            <div className="glass-panel rounded-xl p-5 border border-amber-500/30 relative overflow-hidden group hover:border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.08)] transition-all">
              <div className="flex items-center justify-between text-amber-400 text-xs font-medium mb-2">
                <span>High Risk</span>
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-3xl font-extrabold font-mono text-amber-400 tracking-tight">
                {highCount}
              </div>
              <div className="text-xs text-amber-500/70 mt-1 font-mono">
                Score 0.55 - 0.74 (Priority queue)
              </div>
            </div>

            {/* Metric 4 */}
            <div className="glass-panel rounded-xl p-5 border border-cyan-500/30 relative overflow-hidden group hover:border-cyan-500/50 shadow-[0_0_15px_rgba(6,182,212,0.08)] transition-all">
              <div className="flex items-center justify-between text-cyan-400 text-xs font-medium mb-2">
                <span>Suspicious Scenarios</span>
                <ShieldAlert className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-3xl font-extrabold font-mono text-cyan-300 tracking-tight">
                {suspiciousCount}
              </div>
              <div className="text-xs text-cyan-500/70 mt-1 font-mono">
                Laundering & insider rings
              </div>
            </div>
          </>
        )}
      </div>

      {/* Middle Grid: Risk Distribution + Quick Target Investigation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Risk Distribution Chart */}
        <div className="lg:col-span-7 glass-panel rounded-xl p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <div>
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                QUEUE COMPOSITION
              </span>
              <h3 className="text-base font-bold text-slate-100 mt-0.5">
                Risk Tier Distribution
              </h3>
            </div>
            <span className="text-xs font-mono text-slate-500">
              Total {totalAlerts} accounts
            </span>
          </div>

          {loading ? (
            <div className="h-56 flex items-center justify-center">
              <CardSkeleton />
            </div>
          ) : (
            <div className="h-60 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis
                    dataKey="tier"
                    stroke="#64748b"
                    fontSize={12}
                    tickLine={false}
                    axisLine={{ stroke: "#334155" }}
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={12}
                    tickLine={false}
                    axisLine={{ stroke: "#334155" }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0d1527",
                      borderColor: "rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                      color: "#f1f5f9",
                      fontFamily: "monospace",
                      fontSize: "12px",
                    }}
                    cursor={{ fill: "rgba(255, 255, 255, 0.03)" }}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Selected Target & Quick Launcher */}
        <div className="lg:col-span-5 glass-panel rounded-xl p-6 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                ACTIVE TARGET CHECK
              </span>
              <span className="flex items-center gap-1 text-[10px] font-mono text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/30">
                <Sparkles className="w-3 h-3" />
                VERIFIED SCENARIO
              </span>
            </div>

            <h3 className="text-base font-bold text-slate-100">
              Live Investigation Launcher
            </h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Launch deep explainability across XGBoost SHAP values, deterministic AML rules, and multi-hop network graphs.
            </p>

            {/* Pinned Account Spotlight */}
            <div className="mt-4 p-4 rounded-xl bg-slate-900/90 border border-slate-800/90">
              <div className="text-[10px] font-mono text-slate-500 uppercase">
                Pinned Benchmark Target
              </div>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-extrabold font-mono text-white tracking-wider">
                  {DEFAULT_ACCOUNT}
                </span>
                <RiskTierBadge tier="Critical" size="sm" />
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Scenario S19 (Circular Transfer + Insider Privilege Change)
              </div>

              <Link
                href={`/investigation/${DEFAULT_ACCOUNT}`}
                className="mt-3 flex items-center justify-center gap-2 w-full py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs font-mono transition-all shadow-[0_0_20px_rgba(6,182,212,0.3)]"
              >
                <span>OPEN BENCHMARK INVESTIGATION</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Jump to any account form */}
          <form onSubmit={handleLaunchInvestigation} className="mt-4 pt-4 border-t border-slate-800">
            <label className="text-[11px] font-mono text-slate-400 block mb-1.5">
              Or investigate another Account ID:
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={targetAccountInput}
                  onChange={(e) => setTargetAccountInput(e.target.value)}
                  placeholder="e.g. 800056370"
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <button
                type="submit"
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-mono text-slate-200 transition-colors"
              >
                Inspect
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Highest-Risk Accounts Table */}
      <div className="glass-panel rounded-xl border border-slate-800 overflow-hidden">
        <div className="p-6 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                PRIORITY QUEUE
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-100 mt-0.5">
              Highest-Risk Accounts
            </h3>
            <p className="text-xs text-slate-400">
              Accounts sorted descending by composite multi-signal risk score.
            </p>
          </div>

          <Link
            href="/alerts"
            className="inline-flex items-center gap-1.5 text-xs font-mono text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <span>View All Alerts ({alerts.length})</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={5} />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800/80 bg-slate-900/60 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                  <th className="py-3 px-5">Alert ID</th>
                  <th className="py-3 px-4">Account</th>
                  <th className="py-3 px-4">Scenario</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Risk Tier</th>
                  <th className="py-3 px-4">Score</th>
                  <th className="py-3 px-4">Fired Rules</th>
                  <th className="py-3 px-5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 text-xs">
                {topRiskAccounts.map((alert) => (
                  <tr
                    key={alert.alert_id}
                    className="hover:bg-slate-800/30 transition-colors group"
                  >
                    <td className="py-3.5 px-5 font-mono text-slate-400 font-medium">
                      {alert.alert_id}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-200">
                      {alert.account_id}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">
                      {alert.scenario_id || "-"}
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
                    <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate font-mono text-[11px]">
                      {alert.fired_rules && alert.fired_rules.length > 0 ? (
                        <span className="text-amber-300">
                          {alert.fired_rules.join(", ")}
                        </span>
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
        )}
      </div>
    </div>
  );
}
