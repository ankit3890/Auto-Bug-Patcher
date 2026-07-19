"use client";

import { useEffect, useRef } from "react";
import clsx from "clsx";

export interface LogLine {
  text: string;
  type?: "info" | "success" | "error" | "warn" | "dim";
  timestamp?: string;
}

interface LiveLogsProps {
  lines: LogLine[];
  maxHeight?: string;
  title?: string;
}

export default function LiveLogs({ lines, maxHeight = "300px", title }: LiveLogsProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  return (
    <div className="glass rounded-xl overflow-hidden">
      {/* Terminal header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <div className="flex gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
          <div className="h-2.5 w-2.5 rounded-full bg-amber-500/70" />
          <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/70" />
        </div>
        <span className="text-xs text-slate-500 ml-2 font-mono">{title || "pipeline.log"}</span>
        <div className="ml-auto flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-slate-600">live</span>
        </div>
      </div>

      {/* Log output */}
      <div
        className="p-4 overflow-y-auto font-mono"
        style={{ maxHeight, minHeight: "120px" }}
      >
        {lines.length === 0 ? (
          <p className="text-slate-600 text-xs">Waiting for output…</p>
        ) : (
          lines.map((line, i) => (
            <div key={i} className={clsx("log-line", line.type || "dim")}>
              {line.timestamp && (
                <span className="text-slate-600 mr-2">[{line.timestamp}]</span>
              )}
              {line.text}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
