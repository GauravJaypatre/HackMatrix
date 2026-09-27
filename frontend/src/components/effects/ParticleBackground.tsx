"use client";

import { useEffect, useRef, useCallback } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  opacity: number;
  /** base hue: 185–220 (cyan/sky/blue spectrum) */
  hue: number;
}

interface ParticleBackgroundProps {
  /** Max particles (default 80) */
  count?: number;
  /** Max connection distance in px (default 140) */
  connectionDistance?: number;
  /** Mouse repel radius in px (default 120) */
  repelRadius?: number;
  /** Repel force strength (default 0.04) */
  repelStrength?: number;
  className?: string;
}

const MAX_SPEED = 0.45;
const MIN_SPEED = 0.08;

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

export default function ParticleBackground({
  count = 80,
  connectionDistance = 140,
  repelRadius = 120,
  repelStrength = 0.04,
  className = "",
}: ParticleBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const mouseRef = useRef<{ x: number; y: number } | null>(null);
  const rafRef = useRef<number>(0);
  const hiddenRef = useRef(false);

  /** Build the initial particle list, scaled to current canvas logical size */
  const initParticles = useCallback(
    (w: number, h: number): Particle[] =>
      Array.from({ length: count }, () => {
        const angle = Math.random() * Math.PI * 2;
        const speed = MIN_SPEED + Math.random() * (MAX_SPEED - MIN_SPEED);
        return {
          x: Math.random() * w,
          y: Math.random() * h,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          radius: 0.8 + Math.random() * 1.4,
          opacity: 0.25 + Math.random() * 0.45,
          hue: 185 + Math.random() * 35,
        };
      }),
    [count]
  );

  useEffect(() => {
    /** Respect prefers-reduced-motion */
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (reducedMotion) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = 0;
    let h = 0;
    let dpr = 1;

    function resize() {
      if (!canvas) return;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.offsetWidth;
      h = canvas.offsetHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx!.scale(dpr, dpr);
      particlesRef.current.forEach((p) => {
        p.x = clamp(p.x, 0, w);
        p.y = clamp(p.y, 0, h);
      });
    }

    resize();
    particlesRef.current = initParticles(w, h);

    function onMouseMove(e: MouseEvent) {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      mouseRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }
    function onMouseLeave() {
      mouseRef.current = null;
    }
    function onVisibilityChange() {
      hiddenRef.current = document.hidden;
    }

    window.addEventListener("resize", resize);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseleave", onMouseLeave);
    document.addEventListener("visibilitychange", onVisibilityChange);

    function draw() {
      if (!ctx) return;
      rafRef.current = requestAnimationFrame(draw);
      if (hiddenRef.current) return;

      ctx.clearRect(0, 0, w, h);

      const particles = particlesRef.current;
      const mouse = mouseRef.current;
      const connDist2 = connectionDistance * connectionDistance;
      const repelR2 = repelRadius * repelRadius;

      // Update positions
      for (const p of particles) {
        if (mouse) {
          const dx = p.x - mouse.x;
          const dy = p.y - mouse.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < repelR2 && d2 > 0.001) {
            const d = Math.sqrt(d2);
            const force = (repelRadius - d) / repelRadius;
            p.vx += (dx / d) * force * repelStrength;
            p.vy += (dy / d) * force * repelStrength;
          }
        }

        const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
        if (speed > MAX_SPEED) {
          p.vx = (p.vx / speed) * MAX_SPEED;
          p.vy = (p.vy / speed) * MAX_SPEED;
        }

        p.x += p.vx;
        p.y += p.vy;

        // Wrap edges
        if (p.x < -2) p.x = w + 2;
        if (p.x > w + 2) p.x = -2;
        if (p.y < -2) p.y = h + 2;
        if (p.y > h + 2) p.y = -2;
      }

      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < connDist2) {
            const proximity = 1 - Math.sqrt(d2) / connectionDistance;
            const lineAlpha =
              proximity * proximity * 0.28 * ((a.opacity + b.opacity) / 2);
            const hue = (a.hue + b.hue) / 2;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `hsla(${hue}, 80%, 68%, ${lineAlpha})`;
            ctx.lineWidth = 0.6 * proximity + 0.2;
            ctx.stroke();
          }
        }
      }

      // Draw particles
      for (const p of particles) {
        const grad = ctx.createRadialGradient(
          p.x, p.y, 0,
          p.x, p.y, p.radius * 3.5
        );
        grad.addColorStop(0, `hsla(${p.hue}, 90%, 78%, ${p.opacity})`);
        grad.addColorStop(1, `hsla(${p.hue}, 90%, 68%, 0)`);

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius * 3.5, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${p.hue}, 95%, 85%, ${p.opacity})`;
        ctx.fill();
      }
    }

    draw();

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("mousemove", onMouseMove);
      canvas.removeEventListener("mouseleave", onMouseLeave);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [initParticles, connectionDistance, repelRadius, repelStrength]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={`absolute inset-0 w-full h-full ${className}`}
      style={{ zIndex: 0, pointerEvents: "none" }}
    />
  );
}
