// AutoBug AI — SSE (Server-Sent Events) Client

import type { SSEEvent } from "@/types";

export function createSSEConnection(
  issueId: string,
  onEvent: (event: SSEEvent) => void,
  onError?: (err: Error) => void,
  onClose?: () => void
): () => void {
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${BASE_URL}/api/v1/issues/${issueId}/stream`;

  const eventSource = new EventSource(url);

  eventSource.onmessage = (e) => {
    try {
      const data: SSEEvent = JSON.parse(e.data);
      onEvent(data);

      // Close when pipeline finishes
      if (data.event === "pipeline_complete" || data.event === "pipeline_error") {
        eventSource.close();
        onClose?.();
      }
    } catch {
      // Skip malformed messages
    }
  };

  eventSource.onerror = () => {
    onError?.(new Error("SSE connection error"));
    eventSource.close();
    onClose?.();
  };

  // Return cleanup function
  return () => eventSource.close();
}
