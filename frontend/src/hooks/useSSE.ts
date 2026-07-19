"use client";
// AutoBug AI — useSSE custom hook

import { useCallback, useEffect, useRef, useState } from "react";
import { createSSEConnection } from "@/lib/sse";
import type { AgentStep, SSEEvent } from "@/types";
import { ALL_AGENTS } from "@/types";

export function useSSE(issueId: string | null) {
  const [steps, setSteps] = useState<AgentStep[]>(() =>
    ALL_AGENTS.map((a) => ({ ...a, status: "pending" as const }))
  );
  const [isConnected, setIsConnected] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  const handleEvent = useCallback((event: SSEEvent) => {
    if (event.event === "connected") {
      setIsConnected(true);
      return;
    }

    if (event.event === "agent_start") {
      setSteps((prev) =>
        prev.map((s) =>
          s.name === event.agent
            ? { ...s, status: "running", startedAt: event.timestamp }
            : s
        )
      );
      setProgress(event.progress ?? 0);
    }

    if (event.event === "agent_complete") {
      setSteps((prev) =>
        prev.map((s) =>
          s.name === event.agent
            ? { ...s, status: "completed", summary: event.summary, completedAt: event.timestamp }
            : s
        )
      );
      setProgress(event.progress ?? 0);
    }

    if (event.event === "pipeline_complete") {
      setProgress(100);
      setIsDone(true);
      setResult(event.result ?? null);
      setSteps((prev) =>
        prev.map((s) =>
          s.status === "completed" || s.status === "failed"
            ? s
            : { ...s, status: "skipped" as const }
        )
      );
    }

    if (event.event === "pipeline_error") {
      setError(event.error ?? "Pipeline failed");
      setIsDone(true);
      const failedAgent = event.failed_agent;
      setSteps((prev) =>
        prev.map((s) => {
          if (failedAgent && s.name === failedAgent) {
            return { ...s, status: "failed" as const };
          }
          if (s.status === "completed" || s.status === "failed") {
            return s;
          }
          return { ...s, status: "skipped" as const };
        })
      );
    }
  }, []);

  useEffect(() => {
    if (!issueId) return;

    cleanupRef.current = createSSEConnection(
      issueId,
      handleEvent,
      (err) => setError(err.message),
      () => setIsConnected(false)
    );

    return () => cleanupRef.current?.();
  }, [issueId, handleEvent]);

  return { steps, isConnected, isDone, error, progress, result };
}
