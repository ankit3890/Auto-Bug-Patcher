"use client";

import { useMemo } from "react";

interface DiffViewerProps {
  diff: string;
  title?: string;
}

interface DiffLine {
  type: "added" | "removed" | "context" | "header" | "hunk";
  content: string;
  lineNum?: number;
}

function parseDiff(diff: string): DiffLine[] {
  const lines = diff.split("\n");
  const parsed: DiffLine[] = [];
  let addLineNum = 0;
  let remLineNum = 0;

  for (const line of lines) {
    if (line.startsWith("---") || line.startsWith("+++")) {
      parsed.push({ type: "header", content: line });
    } else if (line.startsWith("@@")) {
      // Parse hunk header to get starting line numbers
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match) {
        remLineNum = parseInt(match[1]);
        addLineNum = parseInt(match[2]);
      }
      parsed.push({ type: "hunk", content: line });
    } else if (line.startsWith("+")) {
      parsed.push({ type: "added", content: line.slice(1), lineNum: addLineNum++ });
    } else if (line.startsWith("-")) {
      parsed.push({ type: "removed", content: line.slice(1), lineNum: remLineNum++ });
    } else {
      parsed.push({ type: "context", content: line.startsWith(" ") ? line.slice(1) : line, lineNum: addLineNum++ });
      remLineNum++;
    }
  }
  return parsed;
}

export default function DiffViewer({ diff, title }: DiffViewerProps) {
  const lines = useMemo(() => parseDiff(diff), [diff]);

  if (!diff) {
    return (
      <div className="card py-10 text-center text-slate-500">No diff to display</div>
    );
  }

  return (
    <div className="glass rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white/[0.02] border-b border-white/[0.06]">
        <div className="flex gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
          <div className="h-2.5 w-2.5 rounded-full bg-amber-500/70" />
          <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/70" />
        </div>
        <span className="text-xs text-slate-500 font-mono">{title || "patch.diff"}</span>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-emerald-400">+{lines.filter((l) => l.type === "added").length}</span>
          <span className="text-red-400">-{lines.filter((l) => l.type === "removed").length}</span>
        </div>
      </div>

      {/* Diff lines */}
      <div className="overflow-x-auto font-mono text-xs">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, i) => {
              if (line.type === "header") {
                return (
                  <tr key={i} className="bg-white/[0.03]">
                    <td colSpan={3} className="px-4 py-1 text-slate-400">{line.content}</td>
                  </tr>
                );
              }
              if (line.type === "hunk") {
                return (
                  <tr key={i} className="bg-brand-950/50">
                    <td colSpan={3} className="px-4 py-1 text-brand-400">{line.content}</td>
                  </tr>
                );
              }

              const bg =
                line.type === "added" ? "bg-emerald-950/40 hover:bg-emerald-950/60" :
                line.type === "removed" ? "bg-red-950/40 hover:bg-red-950/60" :
                "hover:bg-white/[0.02]";
              const numColor = line.type === "added" ? "text-emerald-600" : line.type === "removed" ? "text-red-600" : "text-slate-600";
              const sign = line.type === "added" ? "+" : line.type === "removed" ? "-" : " ";
              const textColor = line.type === "added" ? "text-emerald-300" : line.type === "removed" ? "text-red-300" : "text-slate-400";

              return (
                <tr key={i} className={`${bg} transition-colors`}>
                  <td className={`pl-4 pr-3 py-0.5 select-none w-10 text-right ${numColor}`}>
                    {line.lineNum ?? ""}
                  </td>
                  <td className={`px-2 py-0.5 select-none w-5 ${numColor}`}>{sign}</td>
                  <td className={`pr-4 py-0.5 whitespace-pre ${textColor}`}>{line.content}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
