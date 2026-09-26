"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertOctagon,
  ShieldAlert,
  Network,
  Briefcase,
  FileText,
  Radio,
  ChevronRight,
  Terminal,
} from "lucide-react";
import { DEFAULT_ACCOUNT } from "@/lib/utils";

const NAV_ITEMS = [
  {
    name: "Dashboard",
    path: "/dashboard",
    icon: LayoutDashboard,
    badge: "LIVE",
  },
  {
    name: "Alerts",
    path: "/alerts",
    icon: AlertOctagon,
    badge: null,
  },
  {
    name: "Investigation",
    path: `/investigation/${DEFAULT_ACCOUNT}`,
    icon: ShieldAlert,
    badge: "S19",
  },
  {
    name: "Graph Network",
    path: "/graph",
    icon: Network,
    badge: null,
  },
  {
    name: "Cases",
    path: "/cases",
    icon: Briefcase,
    badge: null,
  },
  {
    name: "Evidence Vault",
    path: "/evidence",
    icon: FileText,
    badge: null,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  const isItemActive = (itemPath: string) => {
    if (itemPath === "/dashboard" && pathname === "/dashboard") return true;
    if (itemPath.startsWith("/investigation") && pathname.startsWith("/investigation")) return true;
    if (itemPath === pathname) return true;
    return false;
  };

  return (
    <aside className="w-64 bg-[#080d19] border-r border-slate-800/80 flex flex-col justify-between shrink-0 h-screen sticky top-0 select-none z-30">
      <div>
        {/* Brand header */}
        <div className="p-5 border-b border-slate-800/80">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 p-[1px] shadow-[0_0_15px_rgba(6,182,212,0.3)]">
              <div className="w-full h-full bg-[#090e1a] rounded-[7px] flex items-center justify-center">
                <Radio className="w-4 h-4 text-cyan-400 group-hover:rotate-45 transition-transform duration-300" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-sm tracking-wider text-slate-100 uppercase">
                  Trace-X
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  v2.0
                </span>
              </div>
              <p className="text-[10px] font-mono tracking-widest text-slate-500 uppercase">
                RISK INTELLIGENCE
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation list */}
        <div className="px-3 py-4 space-y-1">
          <div className="px-3 py-1.5 text-[10px] font-mono tracking-wider text-slate-500 uppercase">
            Platform Modules
          </div>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isItemActive(item.path);

            return (
              <Link
                key={item.name}
                href={item.path}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                  active
                    ? "bg-gradient-to-r from-cyan-500/15 to-transparent text-cyan-300 border-l-2 border-cyan-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      active ? "text-cyan-400" : "text-slate-400 group-hover:text-slate-300"
                    }`}
                  />
                  <span>{item.name}</span>
                </div>

                {item.badge && (
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                      active
                        ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                        : "bg-slate-800 text-slate-400 border border-slate-700/60"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>

        {/* Live Target Quick Access Card */}
        <div className="px-4 py-2">
          <div className="glass-panel rounded-xl p-3 border border-slate-800/90 relative overflow-hidden">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Key Test Subject
              </span>
              <span className="text-[9px] font-mono text-rose-400 bg-rose-500/10 px-1 rounded border border-rose-500/20">
                CRITICAL
              </span>
            </div>
            <div className="font-mono text-sm font-bold text-slate-200">
              {DEFAULT_ACCOUNT}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              S19 Circular Laundering
            </div>
            <Link
              href={`/investigation/${DEFAULT_ACCOUNT}`}
              className="mt-2.5 flex items-center justify-center gap-1.5 w-full py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 text-[11px] font-mono font-medium transition-colors"
            >
              <span>Inspect Account</span>
              <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* Footer System Status */}
      <div className="p-4 border-t border-slate-800/80 bg-[#070b14]/50">
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="flex items-center gap-1.5 font-mono text-[11px] text-slate-400">
            <Terminal className="w-3 h-3 text-cyan-400" />
            FastAPI Backend
          </span>
          <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            8000
          </span>
        </div>
        <p className="text-[10px] font-mono text-slate-500">
          Fusion Engine: XGBoost + Graph
        </p>
      </div>
    </aside>
  );
}
