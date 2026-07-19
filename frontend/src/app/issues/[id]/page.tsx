"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useSSE } from "@/hooks/useSSE";
import type { Issue, Job } from "@/types";
import AgentTimeline from "@/components/AgentTimeline";
import LiveLogs from "@/components/LiveLogs";
import type { LogLine } from "@/components/LiveLogs";
import { ArrowLeft, CheckCircle, XCircle, Clock, ExternalLink, GitPullRequest, Trash, Info } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";

export default function IssueMonitorPage() {
  const { id } = useParams<{ id: string }>();
  const [issue, setIssue] = useState<Issue | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const router = useRouter();

  const handleDelete = async () => {
    if (!id) return;
    if (!confirm("Are you sure you want to delete this issue and all its pipeline executions? This action cannot be undone.")) return;
    try {
      await api.issues.delete(id);
      router.push("/dashboard");
    } catch (err) {
      alert("Failed to delete issue");
    }
  };

  const { steps, isConnected, isDone, error: sseError, progress, result } = useSSE(id);

  // Load issue & job initially
  useEffect(() => {
    if (!id) return;
    api.issues.get(id).then(setIssue).catch(console.error);
    api.issues.getJob(id).then(setJob).catch(console.error);
  }, [id]);

  const isJobCompleted = job?.status === "completed";
  const isJobFailed = job?.status === "failed";

  const effectiveIsDone = isDone || isJobCompleted || isJobFailed;
  const effectiveSseError = isJobCompleted || isJobFailed ? null : sseError;
  const effectiveProgress = isJobCompleted ? 100 : progress;

  const effectiveResult = result || (isJobCompleted ? {
    pr_url: (job?.agent_outputs as any)?.pr_url || "",
    root_cause: job?.root_cause_summary || (job?.agent_outputs as any)?.root_cause?.summary || "",
  } : null);

  const effectiveSteps = steps.map((s) => {
    if (job?.completed_agents?.includes(s.name)) {
      return { ...s, status: "completed" as const };
    }
    if (isJobCompleted || isJobFailed) {
      if (job?.error_message && s.name === job.current_agent) {
        return { ...s, status: "failed" as const };
      }
      return { ...s, status: "skipped" as const };
    }
    return s;
  });

  // Build log lines from SSE step events
  useEffect(() => {
    const runningStep = steps.find((s) => s.status === "running");
    const completedSteps = steps.filter((s) => s.status === "completed");

    const newLogs: LogLine[] = [
      { text: "AutoBug AI pipeline started", type: "info", timestamp: new Date(issue?.created_at || Date.now()).toLocaleTimeString() },
      ...completedSteps.map((s) => ({
        text: `✓ ${s.label}${s.summary ? ` — ${s.summary}` : ""}`,
        type: "success" as const,
      })),
      ...(runningStep ? [{ text: `⟳ ${runningStep.label}…`, type: "info" as const }] : []),
      ...(isDone && !sseError ? [{ text: "✓ Pipeline completed successfully", type: "success" as const }] : []),
      ...(sseError ? [{ text: `✗ Pipeline error: ${sseError}`, type: "error" as const }] : []),
    ];

    if (isJobCompleted && completedSteps.length === 0) {
      newLogs.push({ text: "✓ Pipeline completed successfully (loaded from history)", type: "success" as const });
    } else if (isJobFailed && completedSteps.length === 0) {
      newLogs.push({ text: `✗ Pipeline failed (loaded from history): ${job?.error_message || "Unknown error"}`, type: "error" as const });
    }

    if (isJobCompleted || isJobFailed) {
      setLogs(newLogs.filter((l) => !l.text.includes("SSE connection error")));
    } else {
      setLogs(newLogs);
    }
  }, [steps, isDone, sseError, job, issue]);

  const prUrl = ((effectiveResult as any)?.pr_url as string) || ((job?.agent_outputs as any)?.pr_url as string);

  const SEVERITY_COLORS: Record<string, string> = {
    low: "badge-gray", medium: "badge-yellow", high: "badge-yellow", critical: "badge-red",
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white mb-6">
        <ArrowLeft className="h-4 w-4" /> Dashboard
      </Link>

      {/* Issue header */}
      {issue && (
        <div className="card mb-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-xl font-bold text-white mb-2">{issue.title}</h1>
              <div className="flex items-center gap-3 flex-wrap">
                <span className={SEVERITY_COLORS[issue.severity] || "badge-gray"}>
                  {issue.severity}
                </span>
                <span className={clsx(
                  issue.status === "completed" ? "badge-green" :
                  issue.status === "failed" ? "badge-red" : "badge-blue"
                )}>
                  {issue.status}
                </span>
                <span className="text-xs text-slate-500">
                  {formatDistanceToNow(new Date(issue.created_at), { addSuffix: true })}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={handleDelete}
                className="btn-secondary text-xs border-red-900/30 hover:bg-red-950/20 hover:border-red-900 text-red-400 shrink-0"
              >
                <Trash className="h-3.5 w-3.5" />
                Delete Issue
              </button>
              {prUrl && (
                <a
                  href={prUrl as string}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary text-xs shrink-0"
                >
                  <GitPullRequest className="h-3.5 w-3.5" />
                  View Pull Request
                  <ExternalLink className="h-3 w-3 opacity-70" />
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Connection status */}
      <div className="flex items-center gap-2 mb-5 text-xs">
        <span className={clsx(
          "h-2 w-2 rounded-full",
          isConnected ? "bg-emerald-400 animate-pulse" : effectiveIsDone ? "bg-slate-500" : "bg-amber-400 animate-pulse"
        )} />
        <span className="text-slate-400">
          {isConnected ? "Receiving live updates" : effectiveIsDone ? "Pipeline finished" : "Connecting…"}
        </span>
        {!effectiveIsDone && <span className="text-slate-600">· {effectiveProgress.toFixed(0)}% complete</span>}
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Timeline (left) */}
        <div className="lg:col-span-2">
          <h2 className="font-semibold text-white text-sm mb-3 uppercase tracking-widest text-slate-500">Agent Pipeline</h2>
          <div className="card">
            <AgentTimeline steps={effectiveSteps} progress={effectiveProgress} />
          </div>
        </div>

        {/* Logs + results (right) */}
        <div className="lg:col-span-3 space-y-5">
          <div>
            <h2 className="font-semibold text-white text-sm mb-3 uppercase tracking-widest text-slate-500">Live Output</h2>
            <LiveLogs lines={logs} maxHeight="360px" />
          </div>

          {/* Completion results */}
          {effectiveIsDone && !effectiveSseError && (
            <div className="card animate-slide-up">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle className="h-5 w-5 text-emerald-400" />
                <h3 className="font-semibold text-white">Pipeline Complete</h3>
              </div>
              {!!(effectiveResult as any)?.root_cause && (
                <div className="mb-4">
                  <p className="text-xs text-slate-500 mb-1">Root Cause</p>
                  <p className="text-sm text-slate-200">{(effectiveResult as any).root_cause as string}</p>
                </div>
              )}
              <div className="flex gap-2 flex-wrap">
                <Link href={`/issues/${id}/report`} className="btn-primary">
                  View Full Report
                </Link>
                {prUrl && (
                  <a href={prUrl as string} target="_blank" rel="noopener noreferrer" className="btn-secondary">
                    <GitPullRequest className="h-4 w-4" />
                    Pull Request
                  </a>
                )}
              </div>
              {!prUrl && (
                <div className="mt-4 p-3 bg-slate-900/40 border border-slate-800/60 rounded-lg text-xs text-slate-400 flex items-start gap-2 animate-fade-in">
                  <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-300">Automatic Pull Request skipped:</span> No GitHub Token is configured. 
                    To enable automatic PR creation, add your GitHub token in the{" "}
                    <Link href="/settings" className="text-brand-400 hover:underline">Settings</Link> tab.
                  </div>
                </div>
              )}
            </div>
          )}

          {effectiveIsDone && effectiveSseError && (
            <div className="card border-red-700/30 bg-red-900/10 animate-slide-up">
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="h-5 w-5 text-red-400" />
                <h3 className="font-semibold text-red-300">Pipeline Failed</h3>
              </div>
              <p className="text-sm text-red-400">{effectiveSseError}</p>
            </div>
          )}

          {/* Raw issue description */}
          {issue && (
            <details className="glass rounded-xl">
              <summary className="px-4 py-3 text-sm text-slate-400 cursor-pointer hover:text-white select-none">
                Original Bug Report
              </summary>
              <div className="px-4 pb-4">
                <pre className="text-xs text-slate-400 whitespace-pre-wrap break-words font-mono">
                  {issue.description}
                </pre>
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
