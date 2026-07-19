"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bug, LayoutDashboard, GitBranch, Plus, Settings } from "lucide-react";
import clsx from "clsx";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/repositories", label: "Repositories", icon: GitBranch },
  { href: "/issues/new", label: "New Issue", icon: Plus },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 border-b border-white/[0.06] bg-surface-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center gap-2.5 group"
          >
            <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 shadow-lg shadow-brand-900/50 group-hover:bg-brand-500 transition-colors">
              <Bug className="h-4 w-4 text-white" strokeWidth={2.5} />
              <div className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <span className="font-bold text-base text-white tracking-tight">
              AutoBug <span className="text-brand-400">AI</span>
            </span>
          </Link>

          {/* Nav links */}
          <div className="hidden sm:flex items-center gap-1">
            {NAV_LINKS.map(({ href, label, icon: Icon }) => {
              const active = pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={clsx(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150",
                    active
                      ? "bg-brand-600/20 text-brand-300 border border-brand-500/30"
                      : "text-slate-400 hover:text-white hover:bg-white/[0.05]"
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </Link>
              );
            })}
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-2">
            <span className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              v1.0
            </span>
            <Link
              href="/issues/new"
              className="btn-primary text-xs py-1.5 px-3"
            >
              <Plus className="h-3.5 w-3.5" />
              New Issue
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
