"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Repository } from "@/types";
import RepoCard from "@/components/RepoCard";
import { Plus, GitBranch, Search, Loader2, Trash2, RefreshCw } from "lucide-react";

export default function RepositoriesPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [adding, setAdding] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    api.repositories.list()
      .then(setRepos)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUrl.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await api.repositories.create({ github_url: newUrl.trim() });
      setNewUrl("");
      setAdding(false);
      load();
    } catch (err: any) {
      setError(err.message || "Failed to connect repository");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remove this repository?")) return;
    await api.repositories.delete(id);
    setRepos((prev) => prev.filter((r) => r.id !== id));
  };

  const handleSync = async (id: string) => {
    await api.repositories.sync(id);
    setRepos((prev) => prev.map((r) => r.id === id ? { ...r, index_status: "indexing" } : r));
  };

  const cleanSearch = search.trim().replace(/^https?:\/\/(www\.)?github\.com\//, "").replace(/\.git$/, "");
  const filtered = repos.filter(
    (r) => r.full_name.toLowerCase().includes(cleanSearch.toLowerCase())
  );

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="section-title">Repositories</h1>
          <p className="section-subtitle">{repos.length} connected</p>
        </div>
        <button onClick={() => setAdding(!adding)} className="btn-primary">
          <Plus className="h-4 w-4" />
          Connect Repo
        </button>
      </div>

      {/* Add form */}
      {adding && (
        <div className="card mb-6 animate-slide-up">
          <h2 className="font-semibold text-white mb-4">Connect a GitHub Repository</h2>
          <form onSubmit={handleAdd} className="flex gap-3">
            <input
              className="input flex-1"
              placeholder="https://github.com/owner/repo"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
            />
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Connect"}
            </button>
          </form>
          {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
        </div>
      )}

      {/* Search */}
      <div className="relative mb-5">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
        <input
          className="input pl-9"
          placeholder="Search repositories…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Repo list */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-20 rounded-xl" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card flex flex-col items-center py-16 text-center animate-slide-up">
          <GitBranch className="h-14 w-14 text-slate-700 mb-4" />
          <p className="text-slate-400 mb-2">
            {search ? "No repositories match your search" : "No repositories connected yet"}
          </p>
          {!search && (
            <button onClick={() => setAdding(true)} className="btn-primary mt-2">
              <Plus className="h-4 w-4" /> Connect Repository
            </button>
          )}
          {search && (
            <div className="mt-4">
              {(() => {
                const looksLikeRepo = search.includes("/") || search.includes("github.com");
                if (looksLikeRepo) {
                  let cleanUrl = search.trim();
                  if (!cleanUrl.startsWith("http")) {
                    cleanUrl = `https://github.com/${cleanUrl}`;
                  }
                  return (
                    <button
                      onClick={async () => {
                        setSubmitting(true);
                        try {
                          await api.repositories.create({ github_url: cleanUrl });
                          setSearch(""); // clear search
                          load();
                        } catch (err: any) {
                          alert(err.message || "Failed to connect repository");
                        } finally {
                          setSubmitting(false);
                        }
                      }}
                      className="btn-primary"
                      disabled={submitting}
                    >
                      {submitting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <Plus className="h-4 w-4" />
                          Connect "{cleanUrl.replace("https://github.com/", "")}"
                        </>
                      )}
                    </button>
                  );
                }
                return null;
              })()}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((repo) => (
            <div key={repo.id} className="relative group">
              <RepoCard repo={repo} />
              <div className="absolute right-4 top-1/2 -translate-y-1/2 hidden group-hover:flex items-center gap-1">
                <button
                  onClick={(e) => { e.preventDefault(); handleSync(repo.id); }}
                  className="p-1.5 rounded-lg glass-hover text-slate-400 hover:text-white"
                  title="Re-index"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={(e) => { e.preventDefault(); handleDelete(repo.id); }}
                  className="p-1.5 rounded-lg bg-red-900/30 hover:bg-red-800/50 text-red-400"
                  title="Remove"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
