"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Repository, Issue, Job } from "@/types";
import StatsCard from "@/components/StatsCard";
import RepoCard from "@/components/RepoCard";
import {
  Bug, GitBranch, CheckCircle, Clock, Activity,
  Plus, ArrowRight, AlertTriangle, Trash
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";

const STATUS_COLORS: Record<string, string> = {
  pending: "badge-gray",
  analyzing: "badge-blue",
  reproducing: "badge-blue",
  fixing: "badge-yellow",
  validating: "badge-yellow",
  completed: "badge-green",
  failed: "badge-red",
  awaiting_approval: "badge-yellow",
};

export default function DashboardPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.repositories.list(), api.issues.list()])
      .then(([r, i]) => { setRepos(r); setIssues(i); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const activeIssues = issues.filter((i) => !["completed", "failed"].includes(i.status));
  const completedIssues = issues.filter((i) => i.status === "completed");
  const indexedRepos = repos.filter((r) => r.index_status === "indexed");

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="section-title">Dashboard</h1>
          <p className="section-subtitle">Overview of your AutoBug AI workspace</p>
        </div>
        <Link href="/issues/new" className="btn-primary">
          <Plus className="h-4 w-4" />
          Submit Issue
        </Link>
      </div>

      {/* ── Stats ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard
          label="Repositories"
          value={repos.length}
          sub={`${indexedRepos.length} indexed`}
          icon={GitBranch}
          color="brand"
          loading={loading}
        />
        <StatsCard
          label="Total Issues"
          value={issues.length}
          sub={`${activeIssues.length} active`}
          icon={Bug}
          color="rose"
          loading={loading}
        />
        <StatsCard
          label="Fixed"
          value={completedIssues.length}
          sub="with auto PRs"
          icon={CheckCircle}
          color="emerald"
          loading={loading}
        />
        <StatsCard
          label="In Progress"
          value={activeIssues.length}
          sub="running pipelines"
          icon={Activity}
          color="amber"
          loading={loading}
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* ── Repos ── */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white text-lg">Recent Repositories</h2>
            <Link href="/repositories" className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="skeleton h-24 rounded-xl" />
              ))}
            </div>
          ) : repos.length === 0 ? (
            <div className="card flex flex-col items-center justify-center py-12 text-center">
              <GitBranch className="h-12 w-12 text-slate-600 mb-4" />
              <p className="text-slate-400 mb-4">No repositories connected yet</p>
              <Link href="/repositories" className="btn-primary">
                <Plus className="h-4 w-4" /> Connect Repository
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {repos.slice(0, 5).map((repo) => (
                <RepoCard key={repo.id} repo={repo} compact />
              ))}
            </div>
          )}
        </div>

        {/* ── Recent Issues ── */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white text-lg">Recent Issues</h2>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-16 rounded-xl" />)}
            </div>
          ) : issues.length === 0 ? (
            <div className="card flex flex-col items-center justify-center py-10 text-center">
              <Bug className="h-10 w-10 text-slate-600 mb-3" />
              <p className="text-slate-400 text-sm mb-3">No issues submitted</p>
              <Link href="/issues/new" className="btn-primary text-xs">
                <Plus className="h-3.5 w-3.5" /> New Issue
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {issues.slice(0, 8).map((issue) => (
                <div key={issue.id} className="relative group/card">
                  <Link
                    href={`/issues/${issue.id}`}
                    className="glass-hover rounded-xl p-4 pr-12 flex flex-col gap-1.5 group block"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-white line-clamp-1 group-hover:text-brand-300 transition-colors">
                        {issue.title}
                      </p>
                      <span className={STATUS_COLORS[issue.status]}>
                        {issue.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      {formatDistanceToNow(new Date(issue.created_at), { addSuffix: true })}
                    </p>
                  </Link>
                  <button
                    onClick={async (e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      if (confirm("Are you sure you want to delete this issue and all its pipeline executions?")) {
                        try {
                          await api.issues.delete(issue.id);
                          setIssues((prev) => prev.filter((i) => i.id !== issue.id));
                        } catch (err) {
                          alert("Failed to delete issue");
                        }
                      }
                    }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-2 text-slate-500 hover:text-red-400 rounded-lg hover:bg-slate-800/50 transition-all opacity-0 group-hover/card:opacity-100 focus:opacity-100"
                    title="Delete Issue"
                  >
                    <Trash className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
