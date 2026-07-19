// AutoBug AI — TypeScript Type Definitions

export interface Repository {
  id: string;
  github_url: string;
  full_name: string;
  name: string;
  description?: string;
  default_branch: string;
  languages?: Record<string, number>;
  file_count: number;
  loc: number;
  index_status: "pending" | "indexing" | "indexed" | "failed" | "outdated";
  qdrant_collection?: string;
  last_indexed_at?: string;
  created_at: string;
}

export interface Issue {
  id: string;
  repository_id: string;
  title: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "pending" | "analyzing" | "reproducing" | "fixing" | "validating" | "completed" | "failed" | "awaiting_approval";
  error_type?: string;
  error_message?: string;
  stack_trace?: string;
  environment?: Record<string, string>;
  reproduction_steps?: string[];
  github_issue_url?: string;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  issue_id: string;
  celery_task_id?: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  current_agent?: string;
  completed_agents?: string[];
  failed_agent?: string;
  progress_percent: number;
  root_cause_summary?: string;
  confidence_score?: number;
  error_message?: string;
  agent_outputs?: Record<string, unknown>;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface Patch {
  id: string;
  issue_id: string;
  status: "generated" | "validating" | "validated" | "rejected" | "applied";
  unified_diff?: string;
  modified_files?: string[];
  patch_summary?: string;
  root_cause?: string;
  fault_location?: string;
  confidence_score?: number;
  static_analysis_passed?: boolean;
  tests_passed?: boolean;
  test_results?: Record<string, unknown>;
  reviewer_feedback?: string;
  regression_test?: string;
  regression_test_file?: string;
  created_at: string;
}

export interface SSEEvent {
  event: string;
  job_id: string;
  timestamp: string;
  agent?: string;
  step?: number;
  total?: number;
  progress?: number;
  summary?: string;
  result?: Record<string, unknown>;
  error?: string;
  failed_agent?: string;
}

export interface SearchResult {
  content: string;
  file: string;
  language: string;
  chunk_index: number;
  score: number;
}

export interface AgentStep {
  name: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  summary?: string;
  startedAt?: string;
  completedAt?: string;
}

export const ALL_AGENTS: { name: string; label: string }[] = [
  { name: "repository_agent",             label: "Clone Repository" },
  { name: "environment_agent",            label: "Setup Environment" },
  { name: "environment_validator_agent",  label: "Validate Environment" },
  { name: "issue_agent",                  label: "Parse Issue" },
  { name: "planner_agent",                label: "Plan Investigation" },
  { name: "retrieval_agent",              label: "Retrieve Code" },
  { name: "build_agent",                  label: "Build Project" },
  { name: "reproduction_agent",           label: "Reproduce Bug" },
  { name: "localization_agent",           label: "Localize Fault" },
  { name: "root_cause_agent",             label: "Root Cause Analysis" },
  { name: "patch_agent",                  label: "Generate Patch" },
  { name: "static_analysis_agent",        label: "Static Analysis" },
  { name: "test_generator_agent",         label: "Generate Tests" },
  { name: "test_validator_agent",         label: "Validate Tests" },
  { name: "test_runner_agent",            label: "Run Tests" },
  { name: "reviewer_agent",               label: "Code Review" },
  { name: "risk_agent",                   label: "Evaluate Risk" },
  { name: "performance_agent",            label: "Analyze Performance" },
  { name: "decision_engine",              label: "Merge Decision" },
  { name: "git_agent",                    label: "Commit Changes" },
  { name: "pr_agent",                     label: "Open Pull Request" },
  { name: "consistency_checker",          label: "Check Consistency" },
  { name: "report_agent",                 label: "Generate Report" },
];
