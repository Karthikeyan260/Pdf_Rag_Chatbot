"use client";

import { useCallback, useRef, useState } from "react";
import { apiUrl } from "@/lib/api-client";
import { getAccessToken } from "@/store/auth-store";
import type { ChatStreamEvent, Citation } from "@/lib/types";

interface StreamCallbacks {
  onToken?: (contentSoFar: string, delta: string) => void;
  onDone?: (result: { messageId: string; confidence: number; citations: Citation[] }) => void;
  onError?: (error: Error) => void;
}

interface UseChatStreamResult {
  isStreaming: boolean;
  streamedContent: string;
  sendMessage: (conversationId: string, content: string, callbacks?: StreamCallbacks) => Promise<void>;
  cancelStream: () => void;
}

/**
 * Hook wrapping SSE-over-fetch parsing for POST /conversations/{id}/messages.
 * The endpoint returns text/event-stream; EventSource can't be used because it
 * cannot send a POST body or Authorization header, so we parse the stream manually.
 */
export function useChatStream(): UseChatStreamResult {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback(
    async (conversationId: string, content: string, callbacks?: StreamCallbacks) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);
      setStreamedContent("");

      let buffer = "";
      let accumulated = "";

      try {
        const token = getAccessToken();
        const res = await fetch(apiUrl(`/chat/conversations/${conversationId}/messages`), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ content }),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          let detail = `Chat stream failed with status ${res.status}`;
          try {
            const parsed = await res.json();
            if (parsed?.detail) detail = String(parsed.detail);
          } catch {
            // ignore, keep default message
          }
          throw new Error(detail);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split("\n\n");
          // Keep last partial chunk in buffer
          buffer = events.pop() ?? "";

          for (const rawEvent of events) {
            const dataLines = rawEvent
              .split("\n")
              .filter((line) => line.startsWith("data:"))
              .map((line) => line.slice(5).trim());
            if (dataLines.length === 0) continue;
            const jsonStr = dataLines.join("\n");
            if (!jsonStr) continue;

            let parsed: ChatStreamEvent;
            try {
              parsed = JSON.parse(jsonStr) as ChatStreamEvent;
            } catch {
              continue;
            }

            if (parsed.type === "token") {
              accumulated += parsed.content;
              setStreamedContent(accumulated);
              callbacks?.onToken?.(accumulated, parsed.content);
            } else if (parsed.type === "done") {
              callbacks?.onDone?.({
                messageId: parsed.message_id,
                confidence: parsed.confidence,
                citations: parsed.citations,
              });
            }
          }
        }
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          callbacks?.onError?.(error as Error);
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    []
  );

  return { isStreaming, streamedContent, sendMessage, cancelStream };
}
