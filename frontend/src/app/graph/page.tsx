"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node,
  Edge,
  Panel,
  Handle,
  Position,
} from "@xyflow/react";
import {
  Network,
  Search,
  Shield,
  User,
  Building,
  ArrowRightLeft,
  Info,
  RefreshCw,
} from "lucide-react";

import { api, TraceXApiClientError } from "@/lib/api";
import type { EvidencePayload, SubgraphNode } from "@/types/api";
import { RiskTierBadge } from "@/components/common/RiskTierBadge";
import { ErrorState } from "@/components/common/ErrorState";
import { DEFAULT_ACCOUNT, formatScore } from "@/lib/utils";

// Custom node styling components
function AccountNodeComponent({ data }: { data: { label: string; rawId?: string; isOrigin?: boolean } }) {
  return (
    <div
      className={`px-4 py-3 rounded-xl border backdrop-blur-md shadow-lg transition-all ${
        data.isOrigin
          ? "bg-cyan-950/80 border-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.4)]"
          : "bg-slate-900/90 border-blue-500/40 hover:border-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.15)]"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-cyan-400 !w-2.5 !h-2.5" />
      <div className="flex items-center gap-2">
        <Building className={`w-3.5 h-3.5 ${data.isOrigin ? "text-cyan-400" : "text-blue-400"}`} />
        <span className="text-[10px] font-mono tracking-wider uppercase text-slate-400 font-semibold">
          {data.isOrigin ? "Target Account" : "Account"}
        </span>
      </div>
      <div className="font-mono text-xs font-bold text-slate-100 mt-1">
        {data.label || data.rawId}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-cyan-400 !w-2.5 !h-2.5" />
    </div>
  );
}

function CustomerNodeComponent({ data }: { data: { label: string; rawId?: string } }) {
  return (
    <div className="px-4 py-3 rounded-xl border bg-slate-900/90 border-emerald-500/40 hover:border-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.15)] backdrop-blur-md">
      <Handle type="target" position={Position.Top} className="!bg-emerald-400 !w-2.5 !h-2.5" />
      <div className="flex items-center gap-2">
        <User className="w-3.5 h-3.5 text-emerald-400" />
        <span className="text-[10px] font-mono tracking-wider uppercase text-emerald-400 font-semibold">
          Customer Entity
        </span>
      </div>
      <div className="font-mono text-xs font-bold text-slate-100 mt-1 max-w-[180px] truncate">
        {data.label || data.rawId}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-emerald-400 !w-2.5 !h-2.5" />
    </div>
  );
}

function EmployeeNodeComponent({ data }: { data: { label: string; rawId?: string } }) {
  return (
    <div className="px-4 py-3 rounded-xl border bg-rose-950/80 border-rose-500/60 shadow-[0_0_20px_rgba(244,63,94,0.3)] backdrop-blur-md animate-pulse-slow">
      <Handle type="target" position={Position.Top} className="!bg-rose-500 !w-2.5 !h-2.5" />
      <div className="flex items-center gap-2">
        <Shield className="w-3.5 h-3.5 text-rose-400" />
        <span className="text-[10px] font-mono tracking-wider uppercase text-rose-400 font-bold">
          Insider Employee
        </span>
      </div>
      <div className="font-mono text-xs font-bold text-rose-100 mt-1">
        {data.label || data.rawId}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-rose-500 !w-2.5 !h-2.5" />
    </div>
  );
}

function TxnNodeComponent({ data }: { data: { label: string; rawId?: string } }) {
  return (
    <div className="px-4 py-3 rounded-xl border bg-slate-900/90 border-purple-500/40 shadow-[0_0_15px_rgba(168,85,247,0.15)] backdrop-blur-md">
      <Handle type="target" position={Position.Top} className="!bg-purple-400 !w-2.5 !h-2.5" />
      <div className="flex items-center gap-2">
        <ArrowRightLeft className="w-3.5 h-3.5 text-purple-400" />
        <span className="text-[10px] font-mono tracking-wider uppercase text-purple-400 font-semibold">
          Transaction
        </span>
      </div>
      <div className="font-mono text-xs font-bold text-slate-100 mt-1 max-w-[180px] truncate">
        {data.label || data.rawId}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-purple-400 !w-2.5 !h-2.5" />
    </div>
  );
}

const nodeTypes = {
  accountNode: AccountNodeComponent,
  customerNode: CustomerNodeComponent,
  employeeNode: EmployeeNodeComponent,
  txnNode: TxnNodeComponent,
};

function GraphContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialAccount = searchParams.get("account") || DEFAULT_ACCOUNT;
  const [targetAccount, setTargetAccount] = useState(initialAccount);
  const [accountInput, setAccountInput] = useState(initialAccount);

  const [evidence, setEvidence] = useState<EvidencePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<SubgraphNode | null>(null);

  const fetchEvidenceGraph = async (accId: string) => {
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    try {
      const data = await api.getEvidence(accId);
      setEvidence(data);

      const rawNodes = data.evidence_subgraph?.nodes || [];
      const rawEdges = data.evidence_subgraph?.edges || [];

      // Calculate layout positions
      // Radial or structured layer layout
      const originId = `ACCT_${accId.toUpperCase()}`;
      const accounts = rawNodes.filter((n) => n.type === "Account");
      const customers = rawNodes.filter((n) => n.type === "Customer");
      const employees = rawNodes.filter((n) => n.type === "Employee");
      const transactions = rawNodes.filter((n) => n.type !== "Account" && n.type !== "Customer" && n.type !== "Employee");

      const flowNodes: Node[] = [];

      // Layer 1: Employees (top)
      employees.forEach((emp, idx) => {
        flowNodes.push({
          id: emp.id,
          type: "employeeNode",
          position: { x: 220 * idx + 100, y: 30 },
          data: { label: emp.label, rawId: emp.raw_id || emp.id },
        });
      });

      // Layer 2: Customers (middle upper)
      customers.forEach((cust, idx) => {
        flowNodes.push({
          id: cust.id,
          type: "customerNode",
          position: { x: 240 * idx + 50, y: 160 },
          data: { label: cust.label, rawId: cust.raw_id || cust.id },
        });
      });

      // Layer 3: Accounts (center)
      accounts.forEach((acc, idx) => {
        const isOrigin = acc.id === originId || acc.raw_id === accId.toUpperCase();
        flowNodes.push({
          id: acc.id,
          type: "accountNode",
          position: { x: 260 * idx + 80, y: 310 },
          data: {
            label: acc.label,
            rawId: acc.raw_id || acc.id,
            isOrigin,
          },
        });
      });

      // Layer 4: Transactions / Synthetic (bottom)
      transactions.forEach((tx, idx) => {
        flowNodes.push({
          id: tx.id,
          type: "txnNode",
          position: { x: 250 * idx + 100, y: 460 },
          data: { label: tx.label, rawId: tx.raw_id || tx.id },
        });
      });

      // Edges with cyber styling and labels
      const flowEdges: Edge[] = rawEdges.map((e, idx) => {
        const isLaundering = e.type === "SENT_TO" || e.type === "STEP_IN_CYCLE";
        const isAccess = e.type === "CHANGED_ACCESS";

        return {
          id: `edge-${idx}-${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          label: e.type,
          animated: isLaundering || isAccess,
          style: {
            stroke: isAccess ? "#f43f5e" : isLaundering ? "#06b6d4" : "#475569",
            strokeWidth: isLaundering ? 2.5 : 1.5,
          },
          labelStyle: {
            fill: isAccess ? "#f43f5e" : isLaundering ? "#06b6d4" : "#94a3b8",
            fontFamily: "monospace",
            fontSize: 10,
            fontWeight: 700,
          },
          labelBgStyle: {
            fill: "#0d1527",
            fillOpacity: 0.9,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isAccess ? "#f43f5e" : isLaundering ? "#06b6d4" : "#475569",
          },
        };
      });

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err: unknown) {
      if (err instanceof TraceXApiClientError) {
        setError(err.message);
      } else {
        setError(`Failed to load evidence graph for account ${accId}`);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidenceGraph(targetAccount);
  }, [targetAccount]);

  const handleAccountSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = accountInput.trim().toUpperCase();
    if (clean) {
      setTargetAccount(clean);
      router.push(`/graph?account=${clean}`);
    }
  };

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const raw = evidence?.evidence_subgraph?.nodes?.find((n) => n.id === node.id);
      if (raw) {
        setSelectedNode(raw);
      }
    },
    [evidence]
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-500 h-[calc(100vh-8rem)] flex flex-col">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-cyan-400 font-mono text-xs tracking-widest uppercase">
              INVESTIGATION / NETWORK
            </span>
            <span className="w-1 h-1 rounded-full bg-cyan-400" />
            <span className="text-slate-500 font-mono text-xs">TOPOLOGY MATRIX</span>
          </div>
          <h1 className="text-xl md:text-2xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2.5">
            <Network className="w-6 h-6 text-cyan-400" />
            Evidence Subgraph & Entity Network
          </h1>
        </div>

        {/* Target Account Switcher */}
        <form onSubmit={handleAccountSubmit} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={accountInput}
              onChange={(e) => setAccountInput(e.target.value)}
              placeholder="Enter Account ID..."
              className="bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 font-mono text-xs transition-colors"
          >
            Trace Network
          </button>
        </form>
      </div>

      {/* Main Canvas + Inspector */}
      {error ? (
        <div className="flex-1 flex items-center justify-center">
          <ErrorState
            title="Graph Topology Failed To Load"
            message={error}
            onRetry={() => fetchEvidenceGraph(targetAccount)}
          />
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">
          {/* React Flow Container */}
          <div className="lg:col-span-9 glass-panel rounded-2xl border border-slate-800/80 overflow-hidden relative min-h-[480px]">
            {loading && (
              <div className="absolute inset-0 z-20 bg-slate-950/80 backdrop-blur-sm flex flex-col items-center justify-center space-y-3">
                <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
                <span className="font-mono text-xs text-slate-300">
                  Constructing Multi-Hop Evidence Subgraph...
                </span>
              </div>
            )}

            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              className="bg-[#080c14]"
            >
              <Background color="#1e293b" gap={20} size={1} />
              <Controls />
              <MiniMap
                nodeColor={(node) => {
                  if (node.type === "employeeNode") return "#f43f5e";
                  if (node.type === "customerNode") return "#10b981";
                  if (node.type === "txnNode") return "#a855f7";
                  return "#06b6d4";
                }}
              />

              {/* Status Overlay in Flow */}
              {evidence && (
                <Panel position="top-left" className="glass-panel p-3 rounded-xl border border-slate-800 text-xs font-mono space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">Target:</span>
                    <span className="text-cyan-400 font-bold">{targetAccount}</span>
                    <RiskTierBadge tier={evidence.risk_tier} size="sm" />
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Risk Score: {formatScore(evidence.risk_score)} • {nodes.length} Nodes • {edges.length} Edges
                  </div>
                </Panel>
              )}
            </ReactFlow>
          </div>

          {/* Node Inspector Sidebar */}
          <div className="lg:col-span-3 glass-panel rounded-2xl border border-slate-800/80 p-5 flex flex-col justify-between overflow-y-auto">
            <div>
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <Info className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider">
                    Node Inspector
                  </span>
                </div>
              </div>

              {selectedNode ? (
                <div className="space-y-4 font-mono text-xs">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">Node ID</span>
                    <span className="text-cyan-300 font-bold break-all">{selectedNode.id}</span>
                  </div>

                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">Entity Type</span>
                    <span className="text-slate-200">{selectedNode.type}</span>
                  </div>

                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">Label</span>
                    <span className="text-slate-300 leading-relaxed block">{selectedNode.label}</span>
                  </div>

                  {selectedNode.raw_id && (
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase block">Raw Account / Entity ID</span>
                      <span className="text-slate-300">{selectedNode.raw_id}</span>
                    </div>
                  )}

                  {selectedNode.type === "Account" && selectedNode.raw_id && (
                    <div className="pt-2">
                      <button
                        onClick={() => router.push(`/investigation/${selectedNode.raw_id}`)}
                        className="w-full py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 text-xs font-mono font-medium transition-colors"
                      >
                        Inspect This Account →
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-12 text-center text-slate-500 font-mono text-xs">
                  <Network className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                  Click on any node in the graph to inspect detailed entity metadata and access relationships.
                </div>
              )}
            </div>

            {/* Quick legend */}
            <div className="pt-4 border-t border-slate-800/80 space-y-2 text-[11px] font-mono">
              <span className="text-slate-500 uppercase text-[10px] block">Entity Legend</span>
              <div className="flex items-center gap-2 text-rose-400">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                <span>Insider Employee</span>
              </div>
              <div className="flex items-center gap-2 text-cyan-400">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
                <span>Account Node</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-400">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                <span>Customer Entity</span>
              </div>
              <div className="flex items-center gap-2 text-purple-400">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
                <span>Transaction Edge</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function GraphPage() {
  return (
    <Suspense
      fallback={
        <div className="h-[calc(100vh-8rem)] flex items-center justify-center">
          <div className="flex flex-col items-center space-y-3">
            <div className="w-8 h-8 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
            <span className="font-mono text-xs text-slate-400">Loading Network Canvas...</span>
          </div>
        </div>
      }
    >
      <GraphContent />
    </Suspense>
  );
}

