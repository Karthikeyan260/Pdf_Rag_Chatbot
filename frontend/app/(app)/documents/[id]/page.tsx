"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { PdfViewer, type PdfViewerHandle } from "@/components/pdf-viewer/PdfViewer";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { apiClient } from "@/lib/api-client";
import type { Citation, DocumentRead } from "@/lib/types";

export default function DocumentWorkspacePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const documentId = params.id;

  const [doc, setDoc] = React.useState<DocumentRead | null>(null);
  const [loading, setLoading] = React.useState(true);
  const pdfViewerRef = React.useRef<PdfViewerHandle>(null);

  React.useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const result = await apiClient.get<DocumentRead>(`/documents/${documentId}`);
        if (!cancelled) setDoc(result);
      } catch (error) {
        if (!cancelled) toast.error((error as Error).message || "Failed to load document");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  function handleCitationClick(citation: Citation) {
    pdfViewerRef.current?.jumpToPage(citation.page_number, citation.bbox ?? undefined);
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <div className="flex items-center gap-3 border-b px-4 py-2.5">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => router.push("/dashboard")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        {loading ? (
          <span className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
          </span>
        ) : doc ? (
          <>
            <span className="truncate text-sm font-medium">{doc.filename}</span>
            <StatusBadge status={doc.status} />
            {doc.page_count != null && (
              <span className="text-xs text-muted-foreground">{doc.page_count} pages</span>
            )}
          </>
        ) : (
          <span className="text-sm text-destructive">Document not found</span>
        )}
      </div>

      <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-2">
        <div className="h-full overflow-hidden border-r">
          {doc && doc.status === "done" ? (
            <PdfViewer ref={pdfViewerRef} documentId={documentId} />
          ) : (
            <div className="flex h-full items-center justify-center p-8 text-center text-sm text-muted-foreground">
              {loading
                ? "Loading document…"
                : doc
                  ? `Document is still ${doc.status}. The viewer will be available once processing is done.`
                  : "Document unavailable."}
            </div>
          )}
        </div>
        <div className="h-full overflow-hidden">
          <ChatPanel documentId={documentId} onCitationClick={handleCitationClick} />
        </div>
      </div>
    </div>
  );
}
