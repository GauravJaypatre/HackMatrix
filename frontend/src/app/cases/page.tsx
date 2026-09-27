"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Download,
  Plus,
  CheckCircle,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

import { api, TraceXApiClientError } from "@/lib/api";
import type { CaseRecord, CreateCaseRequest } from "@/types/api";
import { RiskTierBadge } from "@/components/common/RiskTierBadge";
import { TableSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState, EmptyState } from "@/components/common/ErrorState";
import { formatScore, formatDate, DEFAULT_ACCOUNT } from "@/lib/utils";

export default function CasesPage() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected case for viewing
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [reviewerInput, setReviewerInput] = useState("");
  const [assigning, setAssigning] = useState(false);
  const [assignSuccess, setAssignSuccess] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Create Case Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAccountId, setNewAccountId] = useState(DEFAULT_ACCOUNT);
  const [newTitle, setNewTitle] = useState(`Investigation for ${DEFAULT_ACCOUNT}`);
  const [newPriority, setNewPriority] = useState<"CRITICAL" | "HIGH" | "MEDIUM" | "LOW">("CRITICAL");
  const [newAssignee, setNewAssignee] = useState("Alex Morgan (Senior AML Lead)");
  const [newNotes, setNewNotes] = useState("Escalated from Trace-X alert detection console.");
  const [creating, setCreating] = useState(false);

  const fetchCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCases();
      setCases(data);
      if (data.length > 0 && !selectedCaseId) {
        setSelectedCaseId(data[0].case_id);
        setReviewerInput(data[0].assigned_to || "");
      }
    } catch (err: unknown) {
      if (err instanceof TraceXApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to fetch cases from backend");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const selectedCase = cases.find((c) => c.case_id === selectedCaseId) || cases[0];

  useEffect(() => {
    if (selectedCase) {
      setReviewerInput(selectedCase.assigned_to || "");
    }
  }, [selectedCase?.case_id]);

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase || !reviewerInput.trim()) return;
    setAssigning(true);
    setAssignSuccess(false);
    try {
      const updated = await api.assignCase(selectedCase.case_id, reviewerInput.trim());
      setCases((prev) =>
        prev.map((c) => (c.case_id === updated.case_id ? updated : c))
      );
      setAssignSuccess(true);
      setTimeout(() => setAssignSuccess(false), 3000);
    } catch (err: unknown) {
      alert(`Assignment failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setAssigning(false);
    }
  };

  const handleExport = async () => {
    if (!selectedCase) return;
    setExporting(true);
    try {
      const exportData = await api.exportCase(selectedCase.case_id);
      const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
        JSON.stringify(exportData, null, 2)
      )}`;
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", jsonString);
      downloadAnchor.setAttribute(
        "download",
        `${selectedCase.case_id}_${selectedCase.account_id}_evidence.json`
      );
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err: unknown) {
      alert(`Export failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setExporting(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const payload: CreateCaseRequest = {
        account_id: newAccountId.trim().toUpperCase(),
        title: newTitle,
        priority: newPriority,
        assigned_to: newAssignee,
        notes: newNotes,
      };
      const created = await api.createCase(payload);
      setCases((prev) => [created, ...prev]);
      setSelectedCaseId(created.case_id);
      setShowCreateModal(false);
    } catch (err: unknown) {
      alert(`Case creation failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-cyan-400 font-mono text-xs tracking-widest uppercase">
              INVESTIGATION / WORKFLOW
            </span>
            <span className="w-1 h-1 rounded-full bg-cyan-400" />
            <span className="text-slate-500 font-mono text-xs">CASE MANAGEMENT</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2.5">
            <Briefcase className="w-7 h-7 text-cyan-400" />
            Active Investigation Cases
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Track analyst ownership, reassignment, and export complete audit-ready evidence packages.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          <button
            onClick={fetchCases}
            disabled={loading}
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title="Refresh cases"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-mono font-bold text-xs shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>NEW CASE</span>
          </button>
        </div>
      </div>

      {error ? (
        <ErrorState
          title="Could Not Load Cases"
          message={error}
          onRetry={fetchCases}
        />
      ) : loading ? (
        <div className="glass-panel rounded-xl p-6 border border-slate-800">
          <TableSkeleton rows={5} />
        </div>
      ) : cases.length === 0 ? (
        <EmptyState
          title="No Investigation Cases Registered"
          message="No active cases currently exist. Open any alert investigation to register a new case, or click below."
          actionText="Create Case for 800085BF0"
          onAction={() => setShowCreateModal(true)}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Cases List */}
          <div className="lg:col-span-5 glass-panel rounded-xl border border-slate-800 overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-slate-200 uppercase">
                Case Records ({cases.length})
              </span>
              <span className="text-[11px] font-mono text-slate-500">
                Sorted by Creation
              </span>
            </div>

            <div className="divide-y divide-slate-800/60 max-h-[600px] overflow-y-auto">
              {cases.map((c) => {
                const isSelected = c.case_id === selectedCase?.case_id;
                return (
                  <div
                    key={c.case_id}
                    onClick={() => {
                      setSelectedCaseId(c.case_id);
                      setReviewerInput(c.assigned_to || "");
                    }}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected
                        ? "bg-slate-800/60 border-l-4 border-cyan-400 pl-3"
                        : "hover:bg-slate-800/30"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-xs font-bold text-slate-100">
                        {c.case_id}
                      </span>
                      <RiskTierBadge tier={c.risk_tier} size="sm" />
                    </div>

                    <h4 className="text-xs font-semibold text-slate-200 truncate mb-1">
                      {c.title}
                    </h4>

                    <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mt-2">
                      <span>Target: {c.account_id}</span>
                      <span className="text-cyan-400">{c.assigned_to || "Unassigned"}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Case Detail & Actions */}
          {selectedCase && (
            <div className="lg:col-span-7 glass-panel rounded-xl border border-slate-800 p-6 space-y-6">
              {/* Header metrics */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-bold">
                      {selectedCase.case_id}
                    </span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      STATUS: {selectedCase.status}
                    </span>
                    <RiskTierBadge tier={selectedCase.risk_tier} size="sm" />
                  </div>
                  <h2 className="text-lg font-bold text-slate-100 mt-2">
                    {selectedCase.title}
                  </h2>
                </div>

                <div className="text-right font-mono">
                  <span className="text-[10px] text-slate-500 uppercase block">Composite Risk</span>
                  <span className="text-2xl font-extrabold text-cyan-300">
                    {formatScore(selectedCase.risk_score)}
                  </span>
                </div>
              </div>

              {/* Case Attributes Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-500 uppercase block">Account</span>
                  <span className="font-mono text-xs font-bold text-slate-200 mt-0.5 block">
                    {selectedCase.account_id}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-500 uppercase block">Priority</span>
                  <span className="font-mono text-xs font-bold text-rose-400 mt-0.5 block">
                    {selectedCase.priority || "HIGH"}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-500 uppercase block">Created</span>
                  <span className="font-mono text-[11px] text-slate-300 mt-0.5 block truncate">
                    {formatDate(selectedCase.created_at)}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
                  <span className="text-[10px] font-mono text-slate-500 uppercase block">Assignee</span>
                  <span className="font-mono text-xs font-semibold text-cyan-300 mt-0.5 block truncate">
                    {selectedCase.assigned_to || "Unassigned"}
                  </span>
                </div>
              </div>

              {/* Notes */}
              <div>
                <span className="text-xs font-mono uppercase text-slate-400 tracking-wider block mb-2">
                  Investigator Notes
                </span>
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {selectedCase.notes || "No initial notes provided."}
                </div>
              </div>

              {/* Workflow Actions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-800">
                {/* Reassignment Form */}
                <form onSubmit={handleAssign} className="space-y-3">
                  <label className="text-xs font-mono uppercase text-slate-400 tracking-wider block">
                    Reassign Reviewer
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={reviewerInput}
                      onChange={(e) => setReviewerInput(e.target.value)}
                      placeholder="Investigator name..."
                      className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                    <button
                      type="submit"
                      disabled={assigning}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-mono text-slate-200 transition-colors"
                    >
                      {assigning ? "Saving..." : "Assign"}
                    </button>
                  </div>
                  {assignSuccess && (
                    <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> Reassigned successfully
                    </span>
                  )}
                </form>

                {/* Evidence Package Export */}
                <div className="space-y-3">
                  <label className="text-xs font-mono uppercase text-slate-400 tracking-wider block">
                    Compliance Export
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={handleExport}
                      disabled={exporting}
                      className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 font-mono text-xs font-bold transition-all shadow-[0_0_15px_rgba(6,182,212,0.15)]"
                    >
                      <Download className={`w-3.5 h-3.5 ${exporting ? "animate-bounce" : ""}`} />
                      <span>{exporting ? "Preparing Package..." : "Export Evidence JSON"}</span>
                    </button>
                    <Link
                      href={`/investigation/${selectedCase.account_id}`}
                      className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300"
                      title="Open full investigation desk"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* New Case Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="glass-panel-glow bg-[#0b1220] border border-cyan-500/30 rounded-2xl p-6 md:p-8 max-w-lg w-full shadow-2xl relative">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-cyan-400" />
                <h3 className="text-lg font-bold text-slate-100">
                  Register New Investigation Case
                </h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-200 text-xs font-mono"
              >
                ✕ CLOSE
              </button>
            </div>

            <form onSubmit={handleCreateCase} className="space-y-4">
              <div>
                <label className="text-xs font-mono text-slate-300 block mb-1">
                  Target Account ID
                </label>
                <input
                  type="text"
                  required
                  value={newAccountId}
                  onChange={(e) => {
                    setNewAccountId(e.target.value);
                    setNewTitle(`Investigation for ${e.target.value.toUpperCase()}`);
                  }}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-slate-300 block mb-1">
                  Case Title
                </label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-mono text-slate-300 block mb-1">
                    Priority
                  </label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value as typeof newPriority)}
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
                    Assignee
                  </label>
                  <input
                    type="text"
                    value={newAssignee}
                    onChange={(e) => setNewAssignee(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-mono text-slate-300 block mb-1">
                  Initial Notes
                </label>
                <textarea
                  rows={3}
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-mono font-bold text-xs shadow-lg transition-all"
                >
                  {creating ? "Creating..." : "Save Case Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
