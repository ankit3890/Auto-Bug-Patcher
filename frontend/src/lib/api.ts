// AutoBug AI — API Client

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "APIError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}/api/v1${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new APIError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Repositories ──────────────────────────────────────────────────────────────
export const api = {
  repositories: {
    list: () => request<import("@/types").Repository[]>("/repositories"),
    get: (id: string) => request<import("@/types").Repository>(`/repositories/${id}`),
    create: (data: { github_url: string; default_branch?: string }) =>
      request<import("@/types").Repository>("/repositories", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: string) => request<void>(`/repositories/${id}`, { method: "DELETE" }),
    sync: (id: string) => request<{ status: string }>(`/repositories/${id}/sync`, { method: "POST" }),
  },

  // ── Issues ────────────────────────────────────────────────────────────────
  issues: {
    list: (repositoryId?: string) =>
      request<import("@/types").Issue[]>(
        `/issues${repositoryId ? `?repository_id=${repositoryId}` : ""}`
      ),
    get: (id: string) => request<import("@/types").Issue>(`/issues/${id}`),
    getJob: (id: string) => request<import("@/types").Job>(`/issues/${id}/job`),
    submit: (data: {
      repository_id: string;
      title: string;
      description: string;
      severity?: string;
      github_issue_url?: string;
    }) =>
      request<{ issue_id: string; job_id: string; status: string }>("/issues", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: string) => request<void>(`/issues/${id}`, { method: "DELETE" }),
    chat: (id: string, data: { message: string; history: any[] }) =>
      request<{ response: string }>(`/issues/${id}/chat`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // ── Patches ───────────────────────────────────────────────────────────────
  patches: {
    list: (issueId?: string) =>
      request<import("@/types").Patch[]>(
        `/patches${issueId ? `?issue_id=${issueId}` : ""}`
      ),
    get: (id: string) => request<import("@/types").Patch>(`/patches/${id}`),
  },

  // ── Search ────────────────────────────────────────────────────────────────
  search: {
    semantic: (query: string, repoId: string, topK = 10) =>
      request<{ results: import("@/types").SearchResult[]; count: number }>(
        "/search/semantic",
        { method: "POST", body: JSON.stringify({ query, repo_id: repoId, top_k: topK }) }
      ),
    symbol: (symbol: string, repoId: string) =>
      request<{ results: import("@/types").SearchResult[]; count: number }>(
        "/search/symbol",
        { method: "POST", body: JSON.stringify({ symbol, repo_id: repoId }) }
      ),
    files: (pathFragment: string, repoId: string) =>
      request<{ results: { file: string; language: string }[]; count: number }>(
        "/search/files",
        { method: "POST", body: JSON.stringify({ path_fragment: pathFragment, repo_id: repoId }) }
      ),
  },
  config: {
    get: () => request<Record<string, string>>("/config"),
    save: (data: {
      MISTRAL_API_KEY?: string;
      OPENAI_API_KEY?: string;
      ANTHROPIC_API_KEY?: string;
      GOOGLE_API_KEY?: string;
      GITHUB_TOKEN?: string;
    }) =>
      request<{ status: string; message: string }>("/config", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
};

export { APIError };
