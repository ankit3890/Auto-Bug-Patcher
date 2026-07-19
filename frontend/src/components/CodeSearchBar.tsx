"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { SearchResult } from "@/types";
import { Search, Code, Loader2 } from "lucide-react";

interface CodeSearchBarProps {
  repoId: string;
}

export default function CodeSearchBar({ repoId }: CodeSearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [expandedIndices, setExpandedIndices] = useState<number[]>([]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const { results: res } = await api.search.semantic(query, repoId, 8);
      setResults(res);
      setExpandedIndices([]);
    } catch (err) {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (index: number) => {
    setExpandedIndices((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  return (
    <div>
      <form onSubmit={handleSearch} className="flex gap-2 mb-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            className="input pl-9"
            placeholder="Search code semantically…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
        </button>
      </form>

      {loading && (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton h-16 rounded-lg" />)}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="card py-6 text-center">
          <p className="text-slate-400 text-sm">No results found for "{query}"</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-2">
          {results.map((r, i) => {
            const isExpanded = expandedIndices.includes(i);
            return (
              <div
                key={i}
                onClick={() => toggleExpand(i)}
                className="glass rounded-xl p-4 hover:bg-white/[0.06] transition-colors cursor-pointer group select-none"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Code className="h-3.5 w-3.5 text-brand-400 shrink-0" />
                    <span className="text-xs text-brand-300 font-mono truncate">{r.file}</span>
                  </div>
                  <span className="text-xs text-slate-500 shrink-0">
                    {(r.score * 100).toFixed(0)}% match
                  </span>
                </div>
                <pre
                  className={`text-xs text-slate-400 font-mono whitespace-pre-wrap break-all ${
                    !isExpanded ? "line-clamp-4" : "max-h-[500px] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800 select-text"
                  }`}
                  onClick={(e) => {
                    // Prevent closing when clicking/selecting code text
                    if (isExpanded) {
                      e.stopPropagation();
                    }
                  }}
                >
                  {r.content}
                </pre>
                <div className="text-[10px] text-brand-400 mt-2 text-right opacity-40 group-hover:opacity-100 transition-opacity">
                  {isExpanded ? "Click card edge to collapse" : "Click card to expand & view full snippet"}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
