"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Repository } from "@/types";
import { Bug, Loader2, ArrowRight, AlertTriangle } from "lucide-react";

const SEVERITY_OPTIONS = ["low", "medium", "high", "critical"] as const;

function NewIssueForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedRepo = searchParams.get("repo") || "";

  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    repository_id: preselectedRepo,
    title: "",
    description: "",
    severity: "medium" as typeof SEVERITY_OPTIONS[number],
    github_issue_url: "",
  });

  useEffect(() => {
    api.repositories.list()
      .then((r) => {
        setRepos(r.filter((repo) => repo.index_status === "indexed"));
        if (!preselectedRepo && r.length > 0) {
          setForm((f) => ({ ...f, repository_id: r[0].id }));
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [preselectedRepo]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.repository_id || !form.title || !form.description) {
      setError("Please fill in all required fields");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await api.issues.submit(form);
      router.push(`/issues/${result.issue_id}`);
    } catch (err: any) {
      setError(err.message || "Failed to submit issue");
      setSubmitting(false);
    }
  };

  const SEVERITY_COLORS = {
    low:      "border-slate-600 bg-slate-800/50 text-slate-300",
    medium:   "border-amber-600/50 bg-amber-900/20 text-amber-300",
    high:     "border-orange-600/50 bg-orange-900/20 text-orange-300",
    critical: "border-red-600/50 bg-red-900/20 text-red-300",
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <div className="mb-8 text-center">
        <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-brand-600/20 border border-brand-500/30 mb-4">
          <Bug className="h-7 w-7 text-brand-400" />
        </div>
        <h1 className="section-title text-3xl">Submit a Bug Report</h1>
        <p className="section-subtitle mt-2">
          AutoBug AI will automatically analyze, reproduce, and fix your bug.
        </p>
      </div>

      {loading ? (
        <div className="card flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-brand-400" />
        </div>
      ) : repos.length === 0 ? (
        <div className="card text-center py-12">
          <AlertTriangle className="h-10 w-10 text-amber-400 mx-auto mb-3" />
          <p className="text-white font-medium mb-2">No indexed repositories</p>
          <p className="text-slate-400 text-sm mb-4">
            You need at least one fully-indexed repository before submitting a bug.
          </p>
          <a href="/repositories" className="btn-primary inline-flex">Go to Repositories</a>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="card space-y-5">
          {/* Repository */}
          <div>
            <label className="label">Repository <span className="text-red-400">*</span></label>
            <select
              className="input"
              value={form.repository_id}
              onChange={(e) => setForm((f) => ({ ...f, repository_id: e.target.value }))}
            >
              <option value="">Select a repository…</option>
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
              placeholder="e.g. NullPointerException in PaymentService.processRefund()"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
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
                  className={`px-4 py-2 rounded-lg border text-sm font-medium capitalize transition-all ${
                    form.severity === sev
                      ? SEVERITY_COLORS[sev]
                      : "border-white/10 text-slate-500 hover:border-white/20 hover:text-slate-400"
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="label">
              Bug Description <span className="text-red-400">*</span>
            </label>
            <textarea
              className="input resize-none"
              rows={10}
              placeholder={`Describe the bug in detail. Include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages / stack trace
- Environment (OS, runtime version, etc.)`}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
            <p className="text-xs text-slate-500 mt-1">
              The more detail you provide, the better AutoBug AI can analyze the issue.
            </p>
          </div>

          {/* GitHub issue URL (optional) */}
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

          <button type="submit" className="btn-primary w-full justify-center py-3 text-base" disabled={submitting}>
            {submitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Submitting…</>
            ) : (
              <>Submit Bug Report <ArrowRight className="h-4 w-4" /></>
            )}
          </button>
        </form>
      )}
    </div>
  );
}

export default function NewIssuePage() {
  return (
    <Suspense fallback={
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
        <div className="card flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-brand-400" />
        </div>
      </div>
    }>
      <NewIssueForm />
    </Suspense>
  );
}
