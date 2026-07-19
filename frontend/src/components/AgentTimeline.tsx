"use client";

import type { AgentStep } from "@/types";
import { CheckCircle, Circle, Loader2, XCircle } from "lucide-react";
import clsx from "clsx";

interface AgentTimelineProps {
  steps: AgentStep[];
  progress: number;
}

const STATUS_ICON = {
  pending:   { Icon: Circle,        color: "text-slate-600" },
  running:   { Icon: Loader2,       color: "text-brand-400" },
  completed: { Icon: CheckCircle,   color: "text-emerald-400" },
  failed:    { Icon: XCircle,       color: "text-red-400" },
  skipped:   { Icon: Circle,        color: "text-slate-700" },
};

export default function AgentTimeline({ steps, progress }: AgentTimelineProps) {
  return (
    <div>
      {/* Progress bar */}
      <div className="mb-5">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-slate-400">Pipeline Progress</span>
          <span className="text-xs font-mono text-brand-300">{progress.toFixed(0)}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-0.5">
        {steps.map((step, index) => {
          const { Icon, color } = STATUS_ICON[step.status];
          const isRunning = step.status === "running";

          return (
            <div
              key={step.name}
              className={clsx(
                "flex items-start gap-3 px-3 py-2.5 rounded-lg transition-all duration-200",
                isRunning && "bg-brand-500/10 border border-brand-500/20",
                step.status === "completed" && "opacity-70",
                (step.status === "pending" || step.status === "skipped") && "opacity-40",
              )}
            >
              {/* Connector line */}
              <div className="flex flex-col items-center pt-0.5">
                <Icon
                  className={clsx("h-4 w-4 shrink-0", color, isRunning && "animate-spin")}
                />
                {index < steps.length - 1 && (
                  <div
                    className={clsx(
                      "w-px flex-1 mt-1",
                      step.status === "completed" ? "bg-emerald-500/30" : "bg-white/[0.06]"
                    )}
                    style={{ minHeight: "12px" }}
                  />
                )}
              </div>

              <div className="flex-1 min-w-0 pb-1">
                <div className="flex items-center justify-between gap-2">
                  <p className={clsx(
                    "text-sm font-medium",
                    step.status === "running" ? "text-white" :
                    step.status === "completed" ? "text-slate-300" :
                    step.status === "failed" ? "text-red-400" :
                    "text-slate-600"
                  )}>
                    {step.label}
                  </p>
                  <span className="text-xs text-slate-600 font-mono">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
                {step.summary && (
                  <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{step.summary}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
