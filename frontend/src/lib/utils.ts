import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { RiskTier } from "@/types/api";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const DEFAULT_ACCOUNT = "800085BF0";

export const RISK_COLORS: Record<RiskTier, {
  text: string;
  bg: string;
  border: string;
  glow: string;
  hex: string;
  dot: string;
}> = {
  Critical: {
    text: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/30",
    glow: "shadow-[0_0_15px_rgba(244,63,94,0.25)]",
    hex: "#f43f5e",
    dot: "bg-rose-500",
  },
  High: {
    text: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    glow: "shadow-[0_0_15px_rgba(245,158,11,0.25)]",
    hex: "#f59e0b",
    dot: "bg-amber-500",
  },
  Medium: {
    text: "text-yellow-300",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/30",
    glow: "shadow-[0_0_15px_rgba(234,179,8,0.2)]",
    hex: "#eab308",
    dot: "bg-yellow-400",
  },
  Low: {
    text: "text-cyan-400",
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/30",
    glow: "shadow-[0_0_15px_rgba(6,182,212,0.2)]",
    hex: "#06b6d4",
    dot: "bg-cyan-400",
  },
  Unknown: {
    text: "text-slate-400",
    bg: "bg-slate-500/10",
    border: "border-slate-500/30",
    glow: "",
    hex: "#94a3b8",
    dot: "bg-slate-400",
  },
};

export function getTierColor(tier?: string): {
  text: string;
  bg: string;
  border: string;
  glow: string;
  hex: string;
  dot: string;
} {
  const normalized = (tier ? tier.charAt(0).toUpperCase() + tier.slice(1).toLowerCase() : "Unknown") as RiskTier;
  return RISK_COLORS[normalized] || RISK_COLORS.Unknown;
}

export function formatScore(score: number | undefined | null): string {
  if (score === undefined || score === null || isNaN(score)) return "0.000";
  return Number(score).toFixed(3);
}

export function formatPercent(score: number | undefined | null): string {
  if (score === undefined || score === null || isNaN(score)) return "0%";
  return `${Math.round(Number(score) * 100)}%`;
}

export function formatCurrency(amount: number | string | undefined | null): string {
  if (amount === undefined || amount === null) return "$0";
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "N/A";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}
