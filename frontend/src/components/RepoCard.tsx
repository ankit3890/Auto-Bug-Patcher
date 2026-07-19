"use client";

import Link from "next/link";
import type { Repository } from "@/types";
import { GitBranch, Clock, CheckCircle, AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";

const STATUS_CONFIG = {
  pending:   { label: "Pending",    icon: Clock,          color: "badge-gray"   },
  indexing:  { label: "Indexing…",  icon: Loader2,        color: "badge-blue"   },
  indexed:   { label: "Indexed",    icon: CheckCircle,    color: "badge-green"  },
  failed:    { label: "Failed",     icon: AlertTriangle,  color: "badge-red"    },
  outdated:  { label: "Outdated",   icon: RefreshCw,      color: "badge-yellow" },
};

interface RepoCardProps {
  repo: Repository;
  compact?: boolean;
}

export default function RepoCard({ repo, compact }: RepoCardProps) {
  const statusCfg = STATUS_CONFIG[repo.index_status] ?? STATUS_CONFIG.pending;
  const StatusIcon = statusCfg.icon;
  const topLangs = Object.entries(repo.languages || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([lang]) => lang);

  return (
    <Link
      href={`/repositories/${repo.id}`}
      className="glass-hover rounded-xl p-4 flex items-center gap-4 group block"
    >
      {/* Repo icon */}
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-500/10 border border-brand-500/20 shrink-0">
        <GitBranch className="h-5 w-5 text-brand-400" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="font-semibold text-white text-sm group-hover:text-brand-300 transition-colors truncate">
            {repo.full_name}
          </p>
          <span className={statusCfg.color}>
            <StatusIcon className={clsx("h-3 w-3", statusCfg.label === "Indexing…" && "animate-spin")} />
            {statusCfg.label}
          </span>
        </div>

        {!compact && repo.description && (
          <p className="text-slate-500 text-xs mt-0.5 line-clamp-1">{repo.description}</p>
        )}

        <div className="flex items-center gap-3 mt-1 flex-wrap">
          {topLangs.map((lang) => (
            <span key={lang} className="text-xs text-slate-500">{lang}</span>
          ))}
          {repo.file_count > 0 && (
            <span className="text-xs text-slate-600">{repo.file_count} files</span>
          )}
          {repo.last_indexed_at && (
            <span className="text-xs text-slate-600">
              Indexed {formatDistanceToNow(new Date(repo.last_indexed_at), { addSuffix: true })}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
