"use client";

import React from "react";
import { getTierColor } from "@/lib/utils";
import type { RiskTier } from "@/types/api";

interface RiskTierBadgeProps {
  tier?: RiskTier | string;
  size?: "sm" | "md" | "lg";
  showDot?: boolean;
  className?: string;
}

export function RiskTierBadge({
  tier = "Unknown",
  size = "md",
  showDot = true,
  className = "",
}: RiskTierBadgeProps) {
  const colors = getTierColor(tier);

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs font-mono",
    md: "px-2.5 py-1 text-xs font-mono tracking-wide uppercase",
    lg: "px-3.5 py-1.5 text-sm font-mono font-semibold tracking-wider uppercase",
  };

  const dotSizes = {
    sm: "w-1.5 h-1.5",
    md: "w-2 h-2",
    lg: "w-2.5 h-2.5",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium border transition-all duration-200 ${colors.bg} ${colors.border} ${colors.text} ${colors.glow} ${sizeClasses[size]} ${className}`}
    >
      {showDot && (
        <span
          className={`rounded-full ${dotSizes[size]} ${colors.dot} animate-pulse`}
        />
      )}
      {tier}
    </span>
  );
}
