"use client";

import type { LucideIcon } from "lucide-react";
import clsx from "clsx";

interface StatsCardProps {
  label: string;
  value: number | string;
  sub?: string;
  icon: LucideIcon;
  color?: "brand" | "rose" | "emerald" | "amber" | "violet" | "cyan";
  loading?: boolean;
}

const COLOR_MAP = {
  brand:   { icon: "text-brand-400",   bg: "bg-brand-500/10 border-brand-500/20" },
  rose:    { icon: "text-rose-400",     bg: "bg-rose-500/10 border-rose-500/20" },
  emerald: { icon: "text-emerald-400",  bg: "bg-emerald-500/10 border-emerald-500/20" },
  amber:   { icon: "text-amber-400",    bg: "bg-amber-500/10 border-amber-500/20" },
  violet:  { icon: "text-violet-400",   bg: "bg-violet-500/10 border-violet-500/20" },
  cyan:    { icon: "text-cyan-400",     bg: "bg-cyan-500/10 border-cyan-500/20" },
};

export default function StatsCard({
  label, value, sub, icon: Icon, color = "brand", loading,
}: StatsCardProps) {
  const { icon: iconColor, bg } = COLOR_MAP[color];

  if (loading) {
    return <div className="skeleton h-24 rounded-xl" />;
  }

  return (
    <div className="glass rounded-xl p-5 flex items-start gap-4 hover:bg-white/[0.06] transition-colors">
      <div className={clsx("flex h-10 w-10 items-center justify-center rounded-lg border shrink-0", bg)}>
        <Icon className={clsx("h-5 w-5", iconColor)} />
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-white tabular-nums">{value}</p>
        <p className="text-sm font-medium text-slate-300">{label}</p>
        {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}
