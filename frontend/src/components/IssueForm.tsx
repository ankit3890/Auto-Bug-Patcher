"use client";

// IssueForm — reusable multi-step bug form component
// Used by /issues/new/page.tsx (full page) and can be embedded elsewhere.

import { useState } from "react";
import type { Repository } from "@/types";
import { Bug, AlertTriangle, Loader2, ArrowRight } from "lucide-react";
import clsx from "clsx";

interface IssueFormProps {
  repos: Repository[];
  onSubmit: (data: {
    repository_id: string;
    title: string;
    description: string;
    severity: string;
    github_issue_url?: string;
  }) => Promise<void>;
  loading?: boolean;
  error?: string;
}

const SEVERITY_OPTIONS = ["low", "medium", "high", "critical"] as const;
const SEVERITY_COLORS: Record<string, string> = {
  low:      "border-slate-600 bg-slate-800/50 text-slate-300",
  medium:   "border-amber-600/50 bg-amber-900/20 text-amber-300",
  high:     "border-orange-600/50 bg-orange-900/20 text-orange-300",
  critical: "border-red-600/50 bg-red-900/20 text-red-300",
};

export default function IssueForm({ repos, onSubmit, loading, error }: IssueFormProps) {
  const [form, setForm] = useState({
    repository_id: repos[0]?.id || "",
    title: "",
    description: "",
    severity: "medium" as typeof SEVERITY_OPTIONS[number],
    github_issue_url: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Repository */}
      <div>
        <label className="label">Repository <span className="text-red-400">*</span></label>
        <select
          className="input"
          value={form.repository_id}
          onChange={(e) => setForm((f) => ({ ...f, repository_id: e.target.value }))}
          required
        >
          <option value="">Select…</option>
          {repos.map((r) => (
            <option key={r.id} value={r.id}>{r.full_name}</option>
          ))}
        </select>
      </div>

      {/* Title */}
      <div>
        <label className="label">Bug Title <span className="text-red-400">*</span></label>
        <input
          className="input"
          placeholder="e.g. KeyError in user session handler"
          value={form.title}
          onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          required
        />
      </div>

      {/* Severity */}
      <div>
        <label className="label">Severity</label>
        <div className="flex gap-2 flex-wrap">
          {SEVERITY_OPTIONS.map((sev) => (
            <button
              key={sev}
              type="button"
              onClick={() => setForm((f) => ({ ...f, severity: sev }))}
              className={clsx(
                "px-4 py-1.5 rounded-lg border text-sm font-medium capitalize transition-all",
                form.severity === sev ? SEVERITY_COLORS[sev] : "border-white/10 text-slate-500 hover:text-slate-400 hover:border-white/20"
              )}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Description */}
      <div>
        <label className="label">Description <span className="text-red-400">*</span></label>
        <textarea
          className="input resize-none"
          rows={8}
          placeholder="Describe the bug with steps to reproduce, expected vs actual behavior, and any stack traces…"
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          required
        />
      </div>

      {/* GitHub issue URL */}
      <div>
        <label className="label">GitHub Issue URL <span className="text-slate-500 font-normal">(optional)</span></label>
        <input
          className="input"
          placeholder="https://github.com/owner/repo/issues/123"
          value={form.github_issue_url}
          onChange={(e) => setForm((f) => ({ ...f, github_issue_url: e.target.value }))}
        />
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-900/20 border border-red-700/30 rounded-lg p-3">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <button type="submit" className="btn-primary w-full justify-center py-3" disabled={loading}>
        {loading ? (
          <><Loader2 className="h-4 w-4 animate-spin" /> Submitting…</>
        ) : (
          <>Submit Bug Report <ArrowRight className="h-4 w-4" /></>
        )}
      </button>
    </form>
  );
}
