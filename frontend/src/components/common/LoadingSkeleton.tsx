import React from "react";

export function LoadingSkeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-slate-800/60 border border-slate-700/30 ${className}`}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="glass-panel rounded-xl p-5 border border-slate-800/80 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-4 bg-slate-800 rounded w-1/3" />
        <div className="h-4 bg-slate-800 rounded w-12" />
      </div>
      <div className="h-8 bg-slate-800 rounded w-1/2 mb-3" />
      <div className="h-3 bg-slate-800/70 rounded w-3/4" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, idx) => (
        <div
          key={idx}
          className="h-14 bg-slate-900/60 border border-slate-800/80 rounded-lg animate-pulse"
        />
      ))}
    </div>
  );
}
