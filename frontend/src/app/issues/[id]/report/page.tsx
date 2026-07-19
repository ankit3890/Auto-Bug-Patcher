"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Issue, Patch } from "@/types";
import DiffViewer from "@/components/DiffViewer";
import {
  ArrowLeft, GitPullRequest, CheckCircle, XCircle,
  ExternalLink, Copy, Check, FileCode, Bug, Shield,
  MessageSquare, Loader2
} from "lucide-react";
import clsx from "clsx";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [issue, setIssue] = useState<Issue | null>(null);
  const [patch, setPatch] = useState<Patch | null>(null);
  const [job, setJob] = useState<any | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"summary" | "diff" | "tests" | "review" | "chat">("summary");
  const [chatHistory, setChatHistory] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  // Load chat history from localStorage on client mount
  useEffect(() => {
    if (!id) return;
    const stored = localStorage.getItem(`autobug:chat:${id}`);
    if (stored) {
      try {
        setChatHistory(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse stored chat history", e);
      }
    }
  }, [id]);

  // Persist chat history changes to localStorage
  const saveChatHistory = (newHistory: typeof chatHistory) => {
    setChatHistory(newHistory);
    if (id) {
      localStorage.setItem(`autobug:chat:${id}`, JSON.stringify(newHistory));
    }
  };

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (activeTab === "chat") {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatHistory, chatLoading, activeTab]);

  useEffect(() => {
    if (!id) return;
    api.issues.get(id).then(setIssue).catch(console.error);
    api.issues.getJob(id).then(setJob).catch(console.error);
    api.patches.list(id).then((patches) => patches.length > 0 && setPatch(patches[0])).catch(console.error);
  }, [id]);

  const report = job?.agent_outputs?.report as string | undefined;
  const rootCause = job?.agent_outputs?.root_cause as Record<string, any> | undefined;
  const prUrl = job?.agent_outputs?.pr_url as string | undefined;

  const handleCopyReport = async () => {
    if (!report) return;
    await navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const TABS = [
    { id: "summary", label: "Summary" },
    { id: "diff", label: "Code Diff" },
    { id: "tests", label: "Tests" },
    { id: "review", label: "Review" },
    { id: "chat", label: "Refine Fix (Chat)" },
  ] as const;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <Link href={`/issues/${id}`} className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white">
          <ArrowLeft className="h-4 w-4" /> Back to Monitor
        </Link>
        <div className="flex gap-2">
          {report && (
            <button onClick={handleCopyReport} className="btn-secondary text-xs">
              {copied ? <><Check className="h-3.5 w-3.5" /> Copied!</> : <><Copy className="h-3.5 w-3.5" /> Copy Report</>}
            </button>
          )}
          {prUrl && (
            <a href={prUrl} target="_blank" rel="noopener noreferrer" className="btn-primary text-xs">
              <GitPullRequest className="h-3.5 w-3.5" /> View PR
              <ExternalLink className="h-3 w-3 opacity-70" />
            </a>
          )}
        </div>
      </div>

      {/* Report header */}
      {issue && (
        <div className="card mb-6 border-brand-500/20">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/10 border border-brand-500/20 shrink-0">
              <Bug className="h-6 w-6 text-brand-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white mb-1">{issue.title}</h1>
              <div className="flex items-center gap-3 text-sm text-slate-400 flex-wrap">
                <span>Severity: <strong className="text-white capitalize">{issue.severity}</strong></span>
                {patch?.confidence_score && (
                  <span>Fix Confidence: <strong className="text-emerald-400">{(patch.confidence_score * 100).toFixed(0)}%</strong></span>
                )}
                {patch?.tests_passed !== undefined && (
                  <span className={clsx("flex items-center gap-1", patch.tests_passed ? "text-emerald-400" : "text-red-400")}>
                    {patch.tests_passed ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                    Tests {patch.tests_passed ? "passing" : "failing"}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-5 border-b border-white/[0.06] pb-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px",
              activeTab === tab.id
                ? "border-brand-400 text-white"
                : "border-transparent text-slate-500 hover:text-slate-300"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "summary" && (
        <div className="space-y-5 animate-fade-in">
          {/* Root cause */}
          {rootCause && (
            <div className="card">
              <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Bug className="h-4 w-4 text-brand-400" /> Root Cause Analysis
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Summary</p>
                  <p className="text-sm text-slate-200">{rootCause.summary || "N/A"}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Category</p>
                  <code className="text-sm text-brand-300">{rootCause.root_cause_category || "Unknown"}</code>
                </div>
                {rootCause.fault_file && (
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Fault Location</p>
                    <code className="text-sm text-amber-300">{rootCause.fault_file}:{rootCause.fault_line}</code>
                  </div>
                )}
                {rootCause.confidence && (
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Confidence</p>
                    <p className="text-sm text-emerald-400 font-semibold">{(rootCause.confidence * 100).toFixed(0)}%</p>
                  </div>
                )}
              </div>
              {rootCause.detailed_explanation && (
                <div className="mt-4 pt-4 border-t border-white/[0.06]">
                  <p className="text-xs text-slate-500 mb-2">Detailed Explanation</p>
                  <p className="text-sm text-slate-300 leading-relaxed">{rootCause.detailed_explanation}</p>
                </div>
              )}
            </div>
          )}

          {/* Patch summary */}
          {patch && (
            <div className="card">
              <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
                <FileCode className="h-4 w-4 text-emerald-400" /> Patch Summary
              </h2>
              <p className="text-sm text-slate-300 mb-3">{patch.patch_summary || "No summary available"}</p>
              {patch.modified_files && patch.modified_files.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Modified Files</p>
                  <div className="flex flex-wrap gap-2">
                    {patch.modified_files.map((f) => (
                      <code key={f} className="text-xs px-2 py-0.5 rounded bg-white/[0.05] text-slate-300">{f}</code>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Full markdown report */}
          {report && (
            <details className="card">
              <summary className="font-semibold text-white cursor-pointer select-none">Full Markdown Report</summary>
              <pre className="mt-4 text-xs text-slate-400 whitespace-pre-wrap break-words font-mono max-h-96 overflow-y-auto">
                {report}
              </pre>
            </details>
          )}
        </div>
      )}

      {activeTab === "diff" && (
        <div className="animate-fade-in">
          {patch?.unified_diff ? (
            <DiffViewer diff={patch.unified_diff} />
          ) : (
            <div className="card py-12 text-center">
              <p className="text-slate-400">No diff available yet</p>
            </div>
          )}
        </div>
      )}

      {activeTab === "tests" && (
        <div className="animate-fade-in">
          {patch?.regression_test ? (
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-white">Generated Regression Test</h3>
                <code className="text-xs text-slate-500">{patch.regression_test_file}</code>
              </div>
              <pre className="code-block text-xs max-h-[500px] overflow-y-auto">
                {patch.regression_test}
              </pre>
            </div>
          ) : (
            <div className="card py-12 text-center">
              <p className="text-slate-400">No tests generated yet</p>
            </div>
          )}
        </div>
      )}

      {activeTab === "review" && (
        <div className="animate-fade-in space-y-4">
          {patch && (
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                { label: "Tests Passed", ok: patch.tests_passed, icon: CheckCircle },
                { label: "Static Analysis", ok: patch.static_analysis_passed, icon: Shield },
                { label: "Code Review", ok: true, icon: CheckCircle },
              ].map(({ label, ok, icon: Icon }) => (
                <div key={label} className="card text-center">
                  <Icon className={clsx("h-8 w-8 mx-auto mb-2", ok ? "text-emerald-400" : "text-red-400")} />
                  <p className="text-sm font-medium text-white">{label}</p>
                  <p className={clsx("text-xs mt-0.5", ok ? "text-emerald-400" : "text-red-400")}>
                    {ok ? "Passed" : "Failed"}
                  </p>
                </div>
              ))}
            </div>
          )}
          {patch?.reviewer_feedback && (
            <div className="card">
              <h3 className="font-semibold text-white mb-3">Reviewer Comments</h3>
              <pre className="text-xs text-slate-400 whitespace-pre-wrap break-words">
                {patch.reviewer_feedback}
              </pre>
            </div>
          )}
        </div>
      )}

      {activeTab === "chat" && (
        <div className="card space-y-4 flex flex-col h-[520px] animate-fade-in">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3 shrink-0">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-brand-400" />
              <h3 className="font-semibold text-white">Refine Fix with AutoBug AI</h3>
            </div>
            {chatHistory.length > 0 && (
              <button
                onClick={() => {
                  if (confirm("Clear all chat history for this issue?")) {
                    saveChatHistory([]);
                  }
                }}
                className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                Clear History
              </button>
            )}
          </div>

          {/* Chat messages */}
          <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-slate-800 flex flex-col">
            {chatHistory.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full my-auto text-center text-slate-500">
                <MessageSquare className="h-10 w-10 mb-2 opacity-50 text-slate-400" />
                <p className="text-sm">Ask questions about this report or ask the AI to refine the patch code!</p>
              </div>
            ) : (
              chatHistory.map((msg, i) => (
                <div
                  key={i}
                  className={clsx(
                    "p-3 rounded-lg max-w-[85%] text-sm animate-fade-in",
                    msg.role === "user"
                      ? "bg-brand-500/10 border border-brand-500/20 text-slate-100 self-end ml-auto"
                      : "bg-slate-900/60 border border-slate-800/80 text-slate-200"
                  )}
                >
                  <p className="text-[10px] text-slate-500 mb-1.5 font-semibold uppercase tracking-wider">
                    {msg.role === "user" ? "You" : "AutoBug AI"}
                  </p>
                  {msg.role === "user" ? (
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  ) : (
                    <MarkdownText text={msg.content} />
                  )}
                </div>
              ))
            )}
            {chatLoading && (
              <div className="bg-slate-900/60 border border-slate-800/80 p-3 rounded-lg max-w-[85%] text-sm flex items-center gap-2 text-slate-400 self-start">
                <Loader2 className="h-4 w-4 animate-spin text-brand-400" />
                Thinking…
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat input */}
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!chatInput.trim() || chatLoading) return;
              const userMsg = chatInput.trim();
              setChatInput("");
              
              const newHistory = [...chatHistory, { role: "user" as const, content: userMsg }];
              saveChatHistory(newHistory);
              setChatLoading(true);

              try {
                const res = await api.issues.chat(id, {
                  message: userMsg,
                  history: chatHistory,
                });
                saveChatHistory([...newHistory, { role: "assistant" as const, content: res.response }]);
              } catch (err) {
                saveChatHistory([
                  ...newHistory,
                  { role: "assistant" as const, content: "Sorry, I encountered an error invoking the LLM chat." },
                ]);
              } finally {
                setChatLoading(false);
              }
            }}
            className="flex gap-2 pt-3 border-t border-white/[0.06] shrink-0"
          >
            <input
              className="input flex-1 bg-slate-950/50"
              placeholder="Ask a question or request a patch change…"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              disabled={chatLoading}
            />
            <button type="submit" className="btn-primary px-4" disabled={chatLoading}>
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

// ── Lightweight Markdown Formatter ──────────────────────────────────────────
function MarkdownText({ text }: { text: string }) {
  const parts = text.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-3">
      {parts.map((part, index) => {
        if (part.startsWith("```")) {
          const match = part.match(/```(\w*)\n([\s\S]*?)```/);
          const lang = match ? match[1] : "";
          const code = match ? match[2] : part.slice(3, -3);
          return (
            <div key={index} className="my-2 border border-slate-800 rounded-lg overflow-hidden font-mono text-xs">
              {lang && (
                <div className="bg-slate-950/80 px-3 py-1 text-slate-400 font-semibold border-b border-slate-800 uppercase text-[10px] tracking-wider">
                  {lang}
                </div>
              )}
              <pre className="bg-slate-950/40 p-3 overflow-x-auto text-slate-300">
                <code>{code}</code>
              </pre>
            </div>
          );
        } else {
          const lines = part.split("\n");
          return (
            <div key={index} className="space-y-1.5">
              {lines.map((line, lIndex) => {
                const cleanLine = line.trim();
                if (!cleanLine) return null;

                if (cleanLine.startsWith("### ")) {
                  return (
                    <h4 key={lIndex} className="text-sm font-bold text-white mt-3 mb-1">
                      {parseInline(cleanLine.slice(4))}
                    </h4>
                  );
                }
                if (cleanLine.startsWith("## ")) {
                  return (
                    <h3 key={lIndex} className="text-base font-bold text-white mt-4 mb-2">
                      {parseInline(cleanLine.slice(3))}
                    </h3>
                  );
                }
                if (cleanLine.startsWith("- ") || cleanLine.startsWith("* ")) {
                  return (
                    <ul key={lIndex} className="list-disc list-inside pl-1 text-slate-300">
                      <li>{parseInline(cleanLine.slice(2))}</li>
                    </ul>
                  );
                }
                if (cleanLine === "---") {
                  return <hr key={lIndex} className="border-t border-slate-800 my-3" />;
                }

                return (
                  <p key={lIndex} className="text-slate-300 leading-relaxed text-sm">
                    {parseInline(line)}
                  </p>
                );
              })}
            </div>
          );
        }
      })}
    </div>
  );
}

function parseInline(text: string): React.ReactNode[] {
  const tokens = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  return tokens.map((token, index) => {
    if (token.startsWith("**") && token.endsWith("**")) {
      return <strong key={index} className="font-semibold text-white">{token.slice(2, -2)}</strong>;
    }
    if (token.startsWith("`") && token.endsWith("`")) {
      return <code key={index} className="px-1.5 py-0.5 rounded bg-white/[0.06] text-amber-300 font-mono text-xs">{token.slice(1, -1)}</code>;
    }
    return token;
  });
}
