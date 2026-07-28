"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api-client";
import { getAccessToken } from "@/store/auth-store";
import type { ProgressMessage } from "@/lib/types";

function wsUrl(documentId: string, token: string): string {
  const httpBase = API_BASE_URL.replace(/\/$/, "");
  const wsBase = httpBase.replace(/^http/, "ws");
  return `${wsBase}/api/v1/ws/documents/${documentId}/progress?token=${encodeURIComponent(token)}`;
}

interface UseProgressWsOptions {
  enabled?: boolean;
  onDone?: (message: ProgressMessage) => void;
}

/**
 * Subscribes to the document processing progress WebSocket. The server pushes
 * {document_id, status, percent, detail} messages and closes the socket once
 * status is "done" or "failed".
 */
export function useProgressWs(
  documentId: string | null,
  options: UseProgressWsOptions = {}
): { progress: ProgressMessage | null; connected: boolean } {
  const [progress, setProgress] = useState<ProgressMessage | null>(null);
  const [connected, setConnected] = useState(false);
  const onDoneRef = useRef(options.onDone);
  onDoneRef.current = options.onDone;

  const enabled = options.enabled ?? true;

  useEffect(() => {
    if (!documentId || !enabled) return;
    const token = getAccessToken();
    if (!token) return;

    let socket: WebSocket | null = null;
    let cancelled = false;

    try {
      socket = new WebSocket(wsUrl(documentId, token));
    } catch {
      return;
    }

    socket.onopen = () => {
      if (!cancelled) setConnected(true);
    };

    socket.onmessage = (event) => {
      if (cancelled) return;
      try {
        const data = JSON.parse(event.data) as ProgressMessage;
        setProgress(data);
        if (data.status === "done" || data.status === "failed") {
          onDoneRef.current?.(data);
        }
      } catch {
        // ignore malformed frames
      }
    };

    socket.onclose = () => {
      if (!cancelled) setConnected(false);
    };

    socket.onerror = () => {
      if (!cancelled) setConnected(false);
    };

    return () => {
      cancelled = true;
      socket?.close();
    };
  }, [documentId, enabled]);

  return { progress, connected };
}
