"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Radio,
  ArrowRight,
  ShieldAlert,
  Network,
  Activity,
  Layers,
  Sparkles,
  ChevronRight,
  Terminal,
} from "lucide-react";
import { DEFAULT_ACCOUNT } from "@/lib/utils";
import ParticleBackground from "@/components/effects/ParticleBackground";

export default function LandingPage() {

  return (
    <div className="min-h-screen bg-[#060911] text-slate-100 relative overflow-hidden flex flex-col justify-between selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* ─── ATMOSPHERIC BACKGROUND ────────────────────────────────────────────── */}
      {/* Deep nebula radial gradient glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[550px] bg-[radial-gradient(ellipse_at_top,rgba(56,189,248,0.15),rgba(99,102,241,0.08)_40%,transparent_75%)] pointer-events-none blur-3xl" style={{ zIndex: 0 }} />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-[radial-gradient(circle,rgba(6,182,212,0.08),transparent_70%)] pointer-events-none blur-2xl" style={{ zIndex: 0 }} />

      {/* ─── INTERACTIVE PARTICLE CANVAS ────────────────────────────────────── */}
      <div className="absolute inset-0 overflow-hidden" style={{ zIndex: 1 }}>
        <ParticleBackground
          count={85}
          connectionDistance={135}
          repelRadius={110}
          repelStrength={0.045}
        />
      </div>

      {/* Cyber grid overlay — sits above particle canvas, below content */}
      <div
        className="absolute inset-0 pointer-events-none opacity-30"
        style={{ zIndex: 2 }}
      >        <div className="w-full h-full" style={{
          backgroundImage: `linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)`,
          backgroundSize: "40px 40px",
          maskImage: "radial-gradient(ellipse 70% 60% at 50% 30%, #000 60%, transparent 100%)",
        }} />
      </div>

      {/* ─── TOP NAVIGATION HEADER ────────────────────────────────────────────── */}
      <header className="w-full max-w-7xl mx-auto px-6 py-6 flex items-center justify-between relative z-20">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400 via-sky-500 to-indigo-600 p-[1px] shadow-[0_0_20px_rgba(6,182,212,0.35)] transition-transform group-hover:scale-105">
            <div className="w-full h-full bg-[#080d19] rounded-[11px] flex items-center justify-center">
              <Radio className="w-4 h-4 text-cyan-400 group-hover:rotate-45 transition-transform duration-300" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-sm tracking-wider text-white uppercase">
                Trace-X
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                v2.0
              </span>
            </div>
            <p className="text-[9px] font-mono tracking-widest text-slate-500 uppercase">
              CRIME INTELLIGENCE PLATFORM
            </p>
          </div>
        </Link>

        {/* Header Links & Action */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/90 border border-slate-800 text-[11px] font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-400">STATUS:</span>
            <span className="text-emerald-300 font-semibold">4-SIGNAL FUSION ONLINE</span>
          </div>

          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 text-xs font-mono font-medium text-slate-200 hover:text-white transition-all hover:border-cyan-500/50 shadow-sm"
          >
            <span>Console</span>
            <ArrowRight className="w-3.5 h-3.5 text-cyan-400" />
          </Link>
        </div>
      </header>

      {/* ─── HERO SECTION ──────────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-5xl mx-auto px-6 pt-12 pb-16 flex flex-col items-center justify-center text-center relative z-10">
        {/* Top Status Pill */}
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-gradient-to-r from-cyan-500/10 via-indigo-500/10 to-transparent border border-cyan-500/30 text-xs font-mono text-cyan-300 shadow-[0_0_20px_rgba(6,182,212,0.15)] mb-8"
        >
          <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span className="tracking-wide">AI-POWERED FINANCIAL CRIME RISK FUSION</span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400">UN-LEAKED LOSO-CV MODELS</span>
        </motion.div>

        {/* Main Hero Headline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="space-y-4 max-w-4xl"
        >
          <h1 className="text-3xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-white leading-[1.08]">
            See the signal.{" "}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 drop-shadow-[0_0_35px_rgba(56,189,248,0.35)]">
              Trace the risk.
            </span>
            <br />
            Investigate faster.
          </h1>

          <p className="text-base sm:text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed pt-2">
            An explainable financial crime investigation platform fusing{" "}
            <span className="text-slate-200 font-medium">deterministic AML rules</span>,{" "}
            <span className="text-slate-200 font-medium">supervised XGBoost</span>,{" "}
            <span className="text-slate-200 font-medium">isolation outliers</span>, and{" "}
            <span className="text-slate-200 font-medium">structural graph topology</span> into an operational risk score.
          </p>
        </motion.div>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="flex flex-col sm:flex-row items-center gap-4 mt-10"
        >
          {/* Primary CTA */}
          <Link
            href="/dashboard"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-400 via-sky-500 to-blue-600 hover:from-cyan-300 hover:via-sky-400 hover:to-blue-500 text-slate-950 font-mono font-bold text-sm tracking-wide shadow-[0_0_30px_rgba(6,182,212,0.4)] transition-all transform hover:-translate-y-0.5"
          >
            <span>Open Investigation Console</span>
            <ArrowRight className="w-4 h-4" />
          </Link>

          {/* Secondary CTA */}
          <Link
            href={`/investigation/${DEFAULT_ACCOUNT}`}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-slate-900/90 hover:bg-slate-850 border border-slate-700 hover:border-slate-600 text-slate-300 hover:text-white font-mono text-sm tracking-wide transition-all shadow-sm"
          >
            <span>Explore S19 Benchmark</span>
            <ChevronRight className="w-4 h-4 text-cyan-400" />
          </Link>
        </motion.div>

        {/* Architecture Pill Preview */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="mt-14 w-full max-w-3xl glass-panel rounded-2xl p-4 sm:p-5 border border-slate-800/90 bg-[#090f1d]/70 backdrop-blur-xl shadow-2xl relative"
        >
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-slate-800/80 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              <span>SIGNAL SYNTHESIS PIPELINE</span>
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <span className="text-slate-500">Target Account:</span>
              <span className="text-cyan-400 font-bold">{DEFAULT_ACCOUNT}</span>
              <span className="px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px]">
                CRITICAL (0.759)
              </span>
            </div>
          </div>

          {/* 4 Pillars Mini-Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-left">
            <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800/80">
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
                <ShieldAlert className="w-3 h-3 text-rose-400" />
                <span>Rule Engine (16%)</span>
              </div>
              <div className="font-mono text-xs font-bold text-rose-400 mt-1">
                2 Rules Triggered
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5 font-mono truncate">
                Privilege Change + AML
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800/80">
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
                <Activity className="w-3 h-3 text-cyan-400" />
                <span>XGBoost (50%)</span>
              </div>
              <div className="font-mono text-xs font-bold text-cyan-300 mt-1">
                78.0% Probability
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5 font-mono truncate">
                SHAP Explanations
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800/80">
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
                <Layers className="w-3 h-3 text-purple-400" />
                <span>IForest (14%)</span>
              </div>
              <div className="font-mono text-xs font-bold text-purple-300 mt-1">
                0.634 Anomaly
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5 font-mono truncate">
                Outlier Confirmed
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800/80">
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
                <Network className="w-3 h-3 text-blue-400" />
                <span>Graph Intel (20%)</span>
              </div>
              <div className="font-mono text-xs font-bold text-blue-300 mt-1">
                Cycle Detected
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5 font-mono truncate">
                Insider Tied (EMP_0047)
              </div>
            </div>
          </div>
        </motion.div>
      </main>

      {/* ─── REAL METRICS & CAPABILITIES FOOTER GRID ───────────────────────────── */}
      <section className="w-full max-w-7xl mx-auto px-6 py-12 border-t border-slate-800/80 relative z-10">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1 */}
          <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800/80 hover:border-slate-700 transition-colors">
            <div className="text-2xl font-extrabold font-mono text-white mb-1">
              1,884
            </div>
            <div className="text-xs font-bold text-slate-200 mb-1">
              Accounts Mapped
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Structural topological features extracted including in/out-degree, betweenness centrality, and DBSCAN clusters.
            </p>
          </div>

          {/* Card 2 */}
          <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800/80 hover:border-slate-700 transition-colors">
            <div className="text-2xl font-extrabold font-mono text-cyan-300 mb-1">
              4-Signal
            </div>
            <div className="text-xs font-bold text-slate-200 mb-1">
              Risk Fusion Architecture
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Unified operational risk scoring: 16% deterministic rules, 50% XGBoost, 14% Isolation Forest, 20% Graph Anomaly.
            </p>
          </div>

          {/* Card 3 */}
          <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800/80 hover:border-slate-700 transition-colors">
            <div className="text-2xl font-extrabold font-mono text-indigo-300 mb-1">
              Multi-Hop
            </div>
            <div className="text-xs font-bold text-slate-200 mb-1">
              BFS Subgraph Traversal
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Collision-free typed entity graphs linking customers, accounts, administrative changes, and synthetic laundering paths.
            </p>
          </div>

          {/* Card 4 */}
          <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800/80 hover:border-slate-700 transition-colors">
            <div className="text-2xl font-extrabold font-mono text-emerald-400 mb-1">
              0.745
            </div>
            <div className="text-xs font-bold text-slate-200 mb-1">
              LOSO-CV ROC-AUC
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Leave-One-Scenario-Out cross validation with strictly un-leaked features across all synthetic and real transactions.
            </p>
          </div>
        </div>

        {/* Bottom copyright / links */}
        <div className="mt-12 pt-6 border-t border-slate-800/50 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-slate-500">
          <div>
            Trace-X Risk Intelligence Platform · All Rights Reserved
          </div>
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="hover:text-cyan-400 transition-colors">
              Dashboard
            </Link>
            <Link href="/alerts" className="hover:text-cyan-400 transition-colors">
              Alerts
            </Link>
            <Link href="/graph" className="hover:text-cyan-400 transition-colors">
              Graph
            </Link>
            <Link href="/cases" className="hover:text-cyan-400 transition-colors">
              Cases
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
