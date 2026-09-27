"use client";

import React from "react";
import { getTierColor } from "@/lib/utils";
import type { RiskTier } from "@/types/api";

interface ScoreGaugeProps {
  score: number;
  tier?: RiskTier | string;
  size?: number;
  strokeWidth?: number;
  label?: string;
  subtitle?: string;
}

export function ScoreGauge({
  score,
  tier = "Unknown",
  size = 200,
  strokeWidth = 14,
  label = "Composite Risk",
  subtitle,
}: ScoreGaugeProps) {
  const clampedScore = Math.max(0, Math.min(1, score || 0));
  const percentage = Math.round(clampedScore * 100);
  const colors = getTierColor(tier);

  // SVG Gauge calculations (semi-circular / 240 degree arc)
  const radius = (size - strokeWidth * 2) / 2;
  const center = size / 2;

  // 240 degree gauge from 150 deg to 390 deg
  const startAngle = 150;
  const endAngle = 390;
  const totalAngle = endAngle - startAngle;
  const currentAngle = startAngle + (percentage / 100) * totalAngle;

  const polarToCartesian = (centerX: number, centerY: number, rad: number, angleInDegrees: number) => {
    const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
    return {
      x: centerX + rad * Math.cos(angleInRadians),
      y: centerY + rad * Math.sin(angleInRadians),
    };
  };

  const describeArc = (x: number, y: number, rad: number, startA: number, endA: number) => {
    const start = polarToCartesian(x, y, rad, endA);
    const end = polarToCartesian(x, y, rad, startA);
    const largeArcFlag = endA - startA <= 180 ? "0" : "1";
    return ["M", start.x, start.y, "A", rad, rad, 0, largeArcFlag, 0, end.x, end.y].join(" ");
  };

  const bgArc = describeArc(center, center, radius, startAngle, endAngle);
  const progressArc = describeArc(center, center, radius, startAngle, Math.max(startAngle + 0.1, currentAngle));

  return (
    <div className="flex flex-col items-center justify-center relative select-none">
      <svg width={size} height={size * 0.85} viewBox={`0 0 ${size} ${size * 0.85}`} className="overflow-visible">
        <defs>
          <linearGradient id="gaugeBgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1e293b" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#0f172a" stopOpacity="0.8" />
          </linearGradient>
          <linearGradient id="scoreGlow" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#06b6d4" />
            <stop offset="50%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#f43f5e" />
          </linearGradient>
          <filter id="gaugeShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor={colors.hex} floodOpacity="0.4" />
          </filter>
        </defs>

        {/* Background Track */}
        <path
          d={bgArc}
          fill="none"
          stroke="#1e293b"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        {/* Zone indicator steps (subtle dashes) */}
        <path
          d={describeArc(center, center, radius, startAngle, startAngle + totalAngle * 0.3)}
          fill="none"
          stroke="#06b6d4"
          strokeWidth={strokeWidth}
          strokeOpacity="0.15"
          strokeLinecap="round"
        />
        <path
          d={describeArc(center, center, radius, startAngle + totalAngle * 0.3, startAngle + totalAngle * 0.55)}
          fill="none"
          stroke="#eab308"
          strokeWidth={strokeWidth}
          strokeOpacity="0.15"
        />
        <path
          d={describeArc(center, center, radius, startAngle + totalAngle * 0.55, startAngle + totalAngle * 0.75)}
          fill="none"
          stroke="#f59e0b"
          strokeWidth={strokeWidth}
          strokeOpacity="0.15"
        />
        <path
          d={describeArc(center, center, radius, startAngle + totalAngle * 0.75, endAngle)}
          fill="none"
          stroke="#f43f5e"
          strokeWidth={strokeWidth}
          strokeOpacity="0.15"
          strokeLinecap="round"
        />

        {/* Progress Arc */}
        <path
          d={progressArc}
          fill="none"
          stroke={colors.hex}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          filter="url(#gaugeShadow)"
          className="transition-all duration-700 ease-out"
        />
      </svg>

      {/* Center value overlay */}
      <div
        className="absolute flex flex-col items-center justify-center text-center"
        style={{ top: `${size * 0.32}px` }}
      >
        <div className="text-4xl font-extrabold font-mono tracking-tight text-white drop-shadow-md">
          {percentage}
          <span className="text-xl text-slate-400 font-sans ml-0.5">%</span>
        </div>
        <div className="text-xs uppercase tracking-widest font-mono text-slate-400 mt-1">
          {label}
        </div>
        {subtitle && (
          <div className="text-[11px] text-slate-500 font-mono mt-0.5">
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
}
