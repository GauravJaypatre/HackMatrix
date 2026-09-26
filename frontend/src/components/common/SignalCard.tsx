"use client";

import React from "react";
import { LucideIcon } from "lucide-react";

interface SignalCardProps {
  title: string;
  subtitle?: string;
  value: string | number;
  status: "triggered" | "clear" | "warning" | "neutral";
  icon?: LucideIcon;
  detail?: string;
  weight?: string;
  className?: string;
}

export function SignalCard({
  title,
  subtitle,
  value,
  status,
  icon: Icon,
  detail,
  weight,
  className = "",
}: SignalCardProps) {
  const statusStyles = {
    triggered: {
      badge: "bg-rose-500/15 text-rose-400 border-rose-500/30",
      glow: "border-rose-500/30 hover:border-rose-500/50 shadow-[0_0_15px_rgba(244,63,94,0.1)]",
      valColor: "text-rose-400",
      dot: "bg-rose-500",
    },
    warning: {
      badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
      glow: "border-amber-500/30 hover:border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.1)]",
      valColor: "text-amber-400",
      dot: "bg-amber-500",
    },
    clear: {
      badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
      glow: "border-emerald-500/20 hover:border-emerald-500/40",
      valColor: "text-emerald-400",
      dot: "bg-emerald-500",
    },
    neutral: {
      badge: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
      glow: "border-slate-800 hover:border-cyan-500/30",
      valColor: "text-cyan-300",
      dot: "bg-cyan-400",
    },
  };

  const current = statusStyles[status] || statusStyles.neutral;

  return (
    <div
      className={`glass-panel rounded-xl p-5 border transition-all duration-300 relative overflow-hidden group ${current.glow} ${className}`}
    >
      {/* Subtle background glow effect on hover */}
      <div className="absolute -top-12 -right-12 w-28 h-28 bg-cyan-500/5 rounded-full blur-2xl group-hover:bg-cyan-500/10 transition-colors pointer-events-none" />

      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {Icon && (
            <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/50 text-cyan-400">
              <Icon className="w-4 h-4" />
            </div>
          )}
          <div>
            <h4 className="text-sm font-semibold text-slate-200 tracking-wide">
              {title}
            </h4>
            {subtitle && (
              <p className="text-xs text-slate-400">{subtitle}</p>
            )}
          </div>
        </div>

        {weight && (
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800/60 border border-slate-700/40">
            {weight}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-baseline justify-between">
        <div className={`text-2xl font-bold font-mono tracking-tight ${current.valColor}`}>
          {value}
        </div>
        <div
          className={`text-[11px] font-mono font-medium px-2 py-0.5 rounded-full border uppercase tracking-wider inline-flex items-center gap-1.5 ${current.badge}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${current.dot}`} />
          {status.toUpperCase()}
        </div>
      </div>

      {detail && (
        <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
          {detail}
        </p>
      )}
    </div>
  );
}
