"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  Search,
  Clock,
  Copy,
  Check,
  Database,
  ExternalLink,
} from "lucide-react";

import { api, TraceXApiClientError } from "@/lib/api";
import type { EvidencePayload } from "@/types/api";
import { RiskTierBadge } from "@/components/common/RiskTierBadge";
import { ErrorState } from "@/components/common/ErrorState";
import { TableSkeleton } from "@/components/common/LoadingSkeleton";
import { DEFAULT_ACCOUNT, formatScore } from "@/lib/utils";

function EvidenceContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialAccount = searchParams.get("account") || DEFAULT_ACCOUNT;
  const [targetAccount, setTargetAccount] = useState(initialAccount);
  const [accountInput, setAccountInput] = useState(initialAccount);

  const [evidence, setEvidence] = useState<EvidencePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchEvidence = async (accId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getEvidence(accId);
      setEvidence(data);
    } catch (err: unknown) {
      if (err instanceof TraceXApiClientError) {
        setError(err.message);
      } else {
        setError(`Failed to retrieve evidence room payload for account ${accId}`);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence(targetAccount);
  }, [targetAccount]);

  const handleAccountSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = accountInput.trim().toUpperCase();
    if (clean) {
      setTargetAccount(clean);
      router.push(`/evidence?account=${clean}`);
    }
  };

  const handleCopyJson = () => {
    if (!evidence) return;
    navigator.clipboard.writeText(JSON.stringify(evidence, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-cyan-400 font-mono text-xs tracking-widest uppercase">
              INVESTIGATION / EVIDENCE
            </span>
            <span className="w-1 h-1 rounded-full bg-cyan-400" />
            <span className="text-slate-500 font-mono text-xs">AUDIT TRAIL</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2.5">
            <FileText className="w-7 h-7 text-cyan-400" />
            Evidence Room & Audit Trail
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Chronological forensic trail and raw tamper-evident JSON payload for compliance and SAR filing.
          </p>
        </div>

        {/* Target Switcher */}
        <form onSubmit={handleAccountSubmit} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={accountInput}
              onChange={(e) => setAccountInput(e.target.value)}
              placeholder="Search Account ID..."
              className="bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 font-mono text-xs transition-colors"
          >
            Load Evidence
          </button>
        </form>
      </div>

      {error ? (
        <ErrorState
          title="Could Not Load Evidence Room"
          message={error}
          onRetry={() => fetchEvidence(targetAccount)}
        />
      ) : loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="h-24 bg-slate-900/60 rounded-xl animate-pulse" />
            <div className="h-24 bg-slate-900/60 rounded-xl animate-pulse" />
            <div className="h-24 bg-slate-900/60 rounded-xl animate-pulse" />
          </div>
          <TableSkeleton rows={4} />
        </div>
      ) : !evidence ? null : (
        <div className="space-y-6">
          {/* Top Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="glass-panel rounded-xl p-5 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">
                Target Account
              </span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-xl font-bold font-mono text-white">
                  {evidence.account_id}
                </span>
                <RiskTierBadge tier={evidence.risk_tier} size="sm" />
              </div>
            </div>

            <div className="glass-panel rounded-xl p-5 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">
                Risk Score
              </span>
              <div className="text-2xl font-bold font-mono text-cyan-300 mt-1">
                {formatScore(evidence.risk_score)}
              </div>
            </div>

            <div className="glass-panel rounded-xl p-5 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">
                Timeline Events
              </span>
              <div className="text-2xl font-bold font-mono text-slate-100 mt-1">
                {evidence.timeline?.length || 0}
              </div>
            </div>

            <div className="glass-panel rounded-xl p-5 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">
                Subgraph Relationships
              </span>
              <div className="text-2xl font-bold font-mono text-slate-100 mt-1">
                {evidence.evidence_subgraph?.edges?.length || 0} Edges
              </div>
            </div>
          </div>

          {/* Explanation narrative */}
          <div className="glass-panel rounded-xl p-6 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                ANALYST EXPLANATION
              </span>
              <Link
                href={`/investigation/${evidence.account_id}`}
                className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1"
              >
                <span>Full Multi-Signal Desk</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
            <p className="font-mono text-xs text-slate-300 leading-relaxed p-4 rounded-lg bg-slate-950/70 border border-slate-800">
              {evidence.explanation || "No explanation returned by the API."}
            </p>
          </div>

          {/* Chronological Timeline */}
          <div className="glass-panel rounded-xl p-6 border border-slate-800 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Chronological Forensic Timeline
                </h3>
              </div>
              <span className="text-xs font-mono text-slate-400">
                Sorted by Event Timestamp
              </span>
            </div>

            {evidence.timeline && evidence.timeline.length > 0 ? (
              <div className="space-y-4 relative before:absolute before:inset-0 before:left-4 before:w-0.5 before:bg-slate-800">
                {evidence.timeline.map((event, idx) => (
                  <div key={idx} className="relative pl-10">
                    <div className="absolute left-2.5 top-1.5 w-3.5 h-3.5 rounded-full bg-slate-900 border-2 border-cyan-400 -translate-x-1/2 shadow-[0_0_8px_rgba(6,182,212,0.6)]" />

                    <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800/80 hover:border-slate-700 transition-colors">
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
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

                      <p className="text-xs text-slate-200 font-semibold mb-2">
                        {event.summary}
                      </p>

                      {event.details && (
                        <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/60 font-mono text-[11px] text-slate-400 space-y-1">
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
              <div className="text-center py-8 text-slate-500 font-mono text-xs">
                No timeline events recorded.
              </div>
            )}
          </div>

          {/* Raw JSON Inspector */}
          <div className="glass-panel rounded-xl p-6 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-cyan-400" />
                <h3 className="text-base font-bold text-slate-100">
                  Raw Evidence Object (JSON)
                </h3>
              </div>
              <button
                onClick={handleCopyJson}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-mono text-cyan-300 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "COPIED JSON" : "COPY JSON"}</span>
              </button>
            </div>

            <div className="max-h-96 overflow-y-auto rounded-xl bg-slate-950 p-4 border border-slate-800/80 font-mono text-xs text-slate-300 leading-relaxed">
              <pre className="overflow-x-auto">
                {JSON.stringify(evidence, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EvidencePage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="h-24 bg-slate-900/60 rounded-xl animate-pulse" />
            <div className="h-24 bg-slate-900/60 rounded-xl animate-pulse" />
            <div className="h-24 bg-slate-900/60 rounded-xl animate-pulse" />
          </div>
          <TableSkeleton rows={4} />
        </div>
      }
    >
      <EvidenceContent />
    </Suspense>
  );
}

