"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, Activity, Shield, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { DEFAULT_ACCOUNT } from "@/lib/utils";

export function TopNavbar() {
  const router = useRouter();
  const [searchInput, setSearchInput] = useState("");
  const [apiStatus, setApiStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [latency, setLatency] = useState<number>(0);

  useEffect(() => {
    let mounted = true;
    const checkBackend = async () => {
      try {
        const res = await api.checkHealth();
        if (mounted) {
          setApiStatus(res.status);
          setLatency(res.latencyMs);
        }
      } catch {
        if (mounted) {
          setApiStatus("disconnected");
        }
      }
    };

    checkBackend();
    const interval = setInterval(checkBackend, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = searchInput.trim().toUpperCase();
    if (clean) {
      router.push(`/investigation/${clean}`);
      setSearchInput("");
    }
  };

  return (
    <header className="h-16 border-b border-slate-800/80 bg-[#080d19]/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Search Input Bar */}
      <form onSubmit={handleSearch} className="flex-1 max-w-lg">
        <div className="relative group">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2 group-focus-within:text-cyan-400 transition-colors" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={`Search account ID (e.g. ${DEFAULT_ACCOUNT} or 800056370)...`}
            className="w-full bg-slate-900/80 border border-slate-800 rounded-lg pl-10 pr-24 py-1.5 text-xs font-mono text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all"
          />
          <button
            type="submit"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 text-cyan-300 flex items-center gap-1 transition-colors"
          >
            <span>GO</span>
            <ArrowRight className="w-2.5 h-2.5" />
          </button>
        </div>
      </form>

      {/* Right controls */}
      <div className="flex items-center gap-4">
        {/* Quick test subject button */}
        <button
          onClick={() => router.push(`/investigation/${DEFAULT_ACCOUNT}`)}
          className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/70 hover:bg-slate-800 border border-slate-700/60 text-xs font-mono text-slate-300 transition-colors"
          title="Open default critical investigation account"
        >
          <Shield className="w-3.5 h-3.5 text-rose-400" />
          <span className="text-slate-400">Target:</span>
          <span className="text-cyan-400 font-bold">{DEFAULT_ACCOUNT}</span>
        </button>

        {/* Backend live status indicator */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono">
          <Activity className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 hidden sm:inline">FASTAPI:</span>
          {apiStatus === "checking" && (
            <span className="text-amber-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
              CONNECTING
            </span>
          )}
          {apiStatus === "connected" && (
            <span className="text-emerald-400 flex items-center gap-1 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              ONLINE {latency > 0 && <span className="text-[10px] text-slate-500 font-normal">({latency}ms)</span>}
            </span>
          )}
          {apiStatus === "disconnected" && (
            <span className="text-rose-400 flex items-center gap-1 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
              OFFLINE
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
