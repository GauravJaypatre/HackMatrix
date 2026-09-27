"use client";

import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Backend Connection Failure",
  message = "Failed to load data from the Trace-X FastAPI server. Ensure the backend is running at http://127.0.0.1:8000.",
  onRetry,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      className={`glass-panel rounded-xl p-8 border border-rose-500/30 text-center flex flex-col items-center justify-center max-w-lg mx-auto my-12 shadow-[0_0_30px_rgba(244,63,94,0.1)] ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 mb-4 animate-pulse">
        <AlertTriangle className="w-6 h-6" />
      </div>
      <h3 className="text-lg font-bold text-slate-100 mb-2 tracking-wide">
        {title}
      </h3>
      <p className="text-sm text-slate-400 mb-6 leading-relaxed">
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/40 text-rose-300 font-mono text-xs tracking-wider transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          RETRY CONNECTION
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title = "No Records Found",
  message = "No data points matching your criteria were returned by the API.",
  actionText,
  onAction,
}: {
  title?: string;
  message?: string;
  actionText?: string;
  onAction?: () => void;
}) {
  return (
    <div className="glass-panel rounded-xl p-10 border border-slate-800 text-center flex flex-col items-center justify-center max-w-md mx-auto my-10">
      <div className="w-10 h-10 rounded-full bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-3">
        <span className="font-mono text-sm font-bold">∅</span>
      </div>
      <h3 className="text-base font-semibold text-slate-200 mb-1">{title}</h3>
      <p className="text-xs text-slate-400 mb-4 leading-relaxed">{message}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="text-xs font-mono px-3.5 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
}
