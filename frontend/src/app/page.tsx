import Link from "next/link";
import {
  Bug, Zap, GitPullRequest, Shield, Code, ArrowRight,
  CheckCircle, Clock, Activity
} from "lucide-react";

const FEATURES = [
  {
    icon: Bug,
    title: "Autonomous Bug Detection",
    desc: "Continuously monitors your repo for new issues and automatically triages them by severity.",
    color: "text-rose-400",
    bg: "bg-rose-500/10 border-rose-500/20",
  },
  {
    icon: Code,
    title: "Root Cause Analysis",
    desc: "17 specialized AI agents collaborate to trace every bug back to its root cause with confidence scores.",
    color: "text-brand-400",
    bg: "bg-brand-500/10 border-brand-500/20",
  },
  {
    icon: GitPullRequest,
    title: "Automated PRs",
    desc: "Generates a validated patch, regression tests, and opens a GitHub Pull Request — all without human intervention.",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
  },
  {
    icon: Shield,
    title: "Safe Sandboxed Execution",
    desc: "All code runs in isolated Docker containers with resource limits, network isolation, and auto-cleanup.",
    color: "text-violet-400",
    bg: "bg-violet-500/10 border-violet-500/20",
  },
  {
    icon: Zap,
    title: "Semantic Code Search",
    desc: "Qdrant-powered vector search lets you find any function, class or pattern across the entire codebase.",
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
  },
  {
    icon: Activity,
    title: "Real-Time Progress",
    desc: "Watch each of the 17 AI agents execute live via Server-Sent Events with per-step summaries.",
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
  },
];

const STATS = [
  { label: "AI Agents", value: "17" },
  { label: "Languages Supported", value: "12+" },
  { label: "Avg Fix Time", value: "<5 min" },
  { label: "Validation Steps", value: "4" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="relative pt-24 pb-20 px-4 text-center overflow-hidden">
        <div className="relative max-w-4xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-brand-500/30 bg-brand-500/10 text-brand-300 text-xs font-medium mb-6 animate-fade-in">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-400 animate-pulse" />
            17 AI Agents · LangGraph · Docker Sandbox
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold text-white tracking-tight leading-tight mb-6 animate-slide-up">
            Fix Bugs{" "}
            <span className="text-brand-400">
              Autonomously
            </span>
          </h1>

          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-in">
            AutoBug AI connects to your GitHub repository, detects bugs, performs deep root cause
            analysis with 17 specialized AI agents, and opens validated Pull Requests — all
            without human intervention.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center animate-fade-in">
            <Link href="/repositories" className="btn-primary px-6 py-3 text-base">
              Connect a Repository
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/issues/new" className="btn-secondary px-6 py-3 text-base">
              <Bug className="h-4 w-4" />
              Submit a Bug
            </Link>
          </div>
        </div>
      </section>

      {/* ── Stats ────────────────────────────────────────────────────────── */}
      <section className="py-12 px-4 border-y border-white/[0.06]">
        <div className="max-w-4xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-6">
          {STATS.map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="text-3xl font-extrabold text-white mb-1">
                {value}
              </div>
              <div className="text-sm text-slate-500">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────────── */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-white mb-3">How AutoBug AI Works</h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              A fully autonomous 17-agent pipeline that takes you from bug report to merged PR.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map(({ icon: Icon, title, desc, color, bg }) => (
              <div
                key={title}
                className={`glass-hover rounded-xl p-6 border ${bg} group transition-all duration-200`}
              >
                <div className={`inline-flex items-center justify-center h-10 w-10 rounded-lg ${bg} mb-4`}>
                  <Icon className={`h-5 w-5 ${color}`} />
                </div>
                <h3 className="font-semibold text-white mb-2">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pipeline visualization ────────────────────────────────────────── */}
      <section className="py-20 px-4 bg-white/[0.01] border-t border-white/[0.05]">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-4">17-Agent Pipeline</h2>
          <p className="text-slate-400 mb-10">Each agent is specialized for one task in the bug-fixing workflow.</p>
          <div className="flex flex-wrap justify-center gap-2">
            {[
              "Repository", "Issue Parser", "Planner", "RAG Retrieval", "Environment",
              "Build", "Reproduce", "Localize", "Root Cause", "Patch", "Static Analysis",
              "Test Generator", "Test Runner", "Code Review", "Git", "Pull Request", "Report"
            ].map((step, i) => (
              <div
                key={step}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full glass border border-white/[0.08] text-xs text-slate-300"
              >
                <span className="text-brand-400 font-mono text-[10px]">{String(i + 1).padStart(2, "0")}</span>
                {step}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section className="py-24 px-4 text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to fix bugs automatically?</h2>
          <p className="text-slate-400 mb-8">Connect your GitHub repository and AutoBug AI will handle the rest.</p>
          <Link href="/repositories" className="btn-primary px-8 py-3 text-base">
            Get Started Free
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
