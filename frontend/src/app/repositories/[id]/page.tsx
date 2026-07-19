"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Repository, Issue, SearchResult } from "@/types";
import CodeSearchBar from "@/components/CodeSearchBar";
import { GitBranch, ArrowLeft, Bug, Plus, RefreshCw, Loader2, CheckCircle, Trash } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const STATUS_COLORS = {
  pending: "badge-yellow",
  running: "badge-blue",
  completed: "badge-green",
  failed: "badge-red",
};

export default function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const router = useRouter();

  const handleDelete = async () => {
    if (!repo) return;
    if (!confirm("Are you sure you want to remove this repository and all its issues/records? This action cannot be undone.")) return;
    try {
      await api.repositories.delete(repo.id);
      router.push("/repositories");
    } catch (err) {
      alert("Failed to delete repository");
    }
  };

  useEffect(() => {
    if (!id) return;
    Promise.all([api.repositories.get(id), api.issues.list(id)])
      .then(([r, i]) => { setRepo(r); setIssues(i); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  const handleSync = async () => {
    if (!repo) return;
    setSyncing(true);
    await api.repositories.sync(repo.id).catch(console.error);
    setRepo((r) => r ? { ...r, index_status: "indexing" } : r);
    setSyncing(false);
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-4">
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-20 rounded-xl" />)}
      </div>
    );
  }

  if (!repo) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center">
        <p className="text-slate-400">Repository not found.</p>
        <Link href="/repositories" className="btn-secondary mt-4">Go back</Link>
      </div>
    );
  }

  const topLangs = Object.entries(repo.languages || {}).sort((a, b) => b[1] - a[1]);
  const totalLoc = Object.values(repo.languages || {}).reduce((a, b) => a + b, 0);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link href="/repositories" className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white mb-6">
        <ArrowLeft className="h-4 w-4" /> Repositories
      </Link>

      {/* Header */}
      <div className="card mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/10 border border-brand-500/20">
              <GitBranch className="h-6 w-6 text-brand-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">{repo.full_name}</h1>
              {repo.description && <p className="text-slate-400 text-sm mt-0.5">{repo.description}</p>}
              <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                <span>Branch: <code className="text-slate-400">{repo.default_branch}</code></span>
                <span>{repo.file_count} files</span>
                {repo.last_indexed_at && (
                  <span>Indexed {formatDistanceToNow(new Date(repo.last_indexed_at), { addSuffix: true })}</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className={repo.index_status === "indexed" ? "badge-green" : repo.index_status === "indexing" ? "badge-blue" : "badge-gray"}>
              {repo.index_status === "indexed" ? <CheckCircle className="h-3 w-3" /> : repo.index_status === "indexing" ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
              {repo.index_status}
            </span>
            <button onClick={handleSync} className="btn-secondary text-xs" disabled={syncing}>
              <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "Syncing…" : "Re-index"}
            </button>
            <button onClick={handleDelete} className="btn-secondary text-xs border-red-900/30 hover:bg-red-950/20 hover:border-red-900 text-red-400">
              <Trash className="h-3.5 w-3.5" />
              Remove
            </button>
          </div>
        </div>

        {/* Language bars */}
        {topLangs.length > 0 && (
          <div className="mt-6">
            <div className="flex rounded-full overflow-hidden h-2 mb-3">
              {topLangs.slice(0, 5).map(([lang, count], i) => {
                const colors = ["bg-brand-500", "bg-violet-500", "bg-emerald-500", "bg-amber-500", "bg-rose-500"];
                return (
                  <div
                    key={lang}
                    className={colors[i]}
                    style={{ width: `${(count / totalLoc) * 100}%` }}
                    title={`${lang}: ${((count / totalLoc) * 100).toFixed(1)}%`}
                  />
                );
              })}
            </div>
            <div className="flex flex-wrap gap-3">
              {topLangs.slice(0, 5).map(([lang, count], i) => {
                const colors = ["text-brand-400", "text-violet-400", "text-emerald-400", "text-amber-400", "text-rose-400"];
                return (
                  <span key={lang} className={`text-xs ${colors[i]} flex items-center gap-1`}>
                    <span className={`h-2 w-2 rounded-full ${["bg-brand-500","bg-violet-500","bg-emerald-500","bg-amber-500","bg-rose-500"][i]}`} />
                    {lang} {((count / totalLoc) * 100).toFixed(1)}%
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Semantic Search */}
        <div>
          <h2 className="font-semibold text-white mb-3 text-lg">Semantic Code Search</h2>
          <CodeSearchBar repoId={id} />
        </div>

        {/* Issues */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-white text-lg">Issues ({issues.length})</h2>
            <Link href={`/issues/new?repo=${id}`} className="btn-primary text-xs py-1.5 px-3">
              <Plus className="h-3.5 w-3.5" /> New Issue
            </Link>
          </div>
          {issues.length === 0 ? (
            <div className="card py-8 text-center">
              <Bug className="h-10 w-10 text-slate-700 mx-auto mb-3" />
              <p className="text-slate-400 text-sm">No issues for this repo</p>
            </div>
          ) : (
            <div className="space-y-2">
              {issues.slice(0, 6).map((issue) => (
                <Link key={issue.id} href={`/issues/${issue.id}`} className="glass-hover rounded-xl p-3 flex flex-col gap-1.5 block">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-white line-clamp-1">{issue.title}</p>
                    <span className={STATUS_COLORS[issue.status as keyof typeof STATUS_COLORS] || "badge-gray"}>
                      {issue.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    {formatDistanceToNow(new Date(issue.created_at), { addSuffix: true })}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
