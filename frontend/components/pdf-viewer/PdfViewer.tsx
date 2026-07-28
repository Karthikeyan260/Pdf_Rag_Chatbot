"use client";

import * as React from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { Button } from "@/components/ui/button";
import { apiUrl } from "@/lib/api-client";
import { getAccessToken } from "@/store/auth-store";
import { cn } from "@/lib/utils";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

export interface HighlightRequest {
  page: number;
  bbox?: [number, number, number, number];
  key: number;
}

export interface PdfViewerHandle {
  jumpToPage: (page: number, bbox?: [number, number, number, number]) => void;
}

interface PdfViewerProps {
  documentId: string;
  className?: string;
}

const DEFAULT_SCALE = 1.2;
const MIN_SCALE = 0.5;
const MAX_SCALE = 3;

export const PdfViewer = React.forwardRef<PdfViewerHandle, PdfViewerProps>(
  ({ documentId, className }, ref) => {
    const [numPages, setNumPages] = React.useState<number | null>(null);
    const [pageNumber, setPageNumber] = React.useState(1);
    const [scale, setScale] = React.useState(DEFAULT_SCALE);
    const [pageSize, setPageSize] = React.useState<{ width: number; height: number } | null>(null);
    const [highlight, setHighlight] = React.useState<HighlightRequest | null>(null);
    const [loadError, setLoadError] = React.useState<string | null>(null);
    const highlightTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

    const token = getAccessToken();

    const fileSource = React.useMemo(
      () => ({
        url: apiUrl(`/documents/${documentId}/file`),
        httpHeaders: token ? { Authorization: `Bearer ${token}` } : undefined,
      }),
      [documentId, token]
    );

    React.useImperativeHandle(ref, () => ({
      jumpToPage: (page: number, bbox?: [number, number, number, number]) => {
        setPageNumber(page);
        setHighlight({ page, bbox, key: Date.now() });
        if (highlightTimeoutRef.current) clearTimeout(highlightTimeoutRef.current);
        highlightTimeoutRef.current = setTimeout(() => setHighlight(null), 3200);
      },
    }));

    React.useEffect(() => {
      return () => {
        if (highlightTimeoutRef.current) clearTimeout(highlightTimeoutRef.current);
      };
    }, []);

    function goToPage(delta: number) {
      setPageNumber((prev) => {
        const next = prev + delta;
        if (!numPages) return prev;
        return Math.min(Math.max(1, next), numPages);
      });
    }

    return (
      <div className={cn("flex h-full flex-col bg-muted/20", className)}>
        <div className="flex items-center justify-between gap-2 border-b bg-background px-3 py-2">
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              className="h-7 w-7"
              onClick={() => goToPage(-1)}
              disabled={pageNumber <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="min-w-[5.5rem] text-center text-xs text-muted-foreground">
              Page {pageNumber} {numPages ? `of ${numPages}` : ""}
            </span>
            <Button
              variant="outline"
              size="icon"
              className="h-7 w-7"
              onClick={() => goToPage(1)}
              disabled={!numPages || pageNumber >= numPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              className="h-7 w-7"
              onClick={() => setScale((s) => Math.max(MIN_SCALE, s - 0.2))}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="min-w-[3rem] text-center text-xs text-muted-foreground">
              {Math.round(scale * 100)}%
            </span>
            <Button
              variant="outline"
              size="icon"
              className="h-7 w-7"
              onClick={() => setScale((s) => Math.min(MAX_SCALE, s + 0.2))}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="relative flex-1 overflow-auto">
          <div className="flex justify-center p-4">
            {loadError ? (
              <div className="mt-12 text-sm text-destructive">{loadError}</div>
            ) : (
              <Document
                file={fileSource}
                onLoadSuccess={({ numPages: n }) => setNumPages(n)}
                onLoadError={(err) => setLoadError(err.message || "Failed to load PDF")}
                loading={
                  <div className="flex items-center gap-2 py-24 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" /> Loading document…
                  </div>
                }
              >
                <div className="relative inline-block shadow-lg">
                  <Page
                    pageNumber={pageNumber}
                    scale={scale}
                    onLoadSuccess={(page) => {
                      const viewport = page.getViewport({ scale });
                      setPageSize({ width: viewport.width, height: viewport.height });
                    }}
                    renderAnnotationLayer
                    renderTextLayer
                  />
                  <AnimatePresence>
                    {highlight && highlight.page === pageNumber && highlight.bbox && pageSize && (
                      <HighlightOverlay bbox={highlight.bbox} scale={scale} highlightKey={highlight.key} />
                    )}
                  </AnimatePresence>
                </div>
              </Document>
            )}
          </div>
        </div>
      </div>
    );
  }
);
PdfViewer.displayName = "PdfViewer";

/**
 * bbox is [x0, y0, x1, y1] in PDF point space at 72dpi, with origin at the
 * top-left of the page (the convention used by the backend's PDF text
 * extraction / chunking pipeline, e.g. PyMuPDF/pdfplumber-style rects with
 * y increasing downward). We simply scale point coordinates by the current
 * render scale to get CSS pixel coordinates relative to the rendered page.
 * If the backend ever switches to bottom-left-origin PDF coordinates, flip
 * with `pageHeightInPoints - y` before scaling.
 */
function HighlightOverlay({
  bbox,
  scale,
  highlightKey,
}: {
  bbox: [number, number, number, number];
  scale: number;
  highlightKey: number;
}) {
  const [x0, y0, x1, y1] = bbox;
  const left = Math.min(x0, x1) * scale;
  const top = Math.min(y0, y1) * scale;
  const width = Math.abs(x1 - x0) * scale;
  const height = Math.abs(y1 - y0) * scale;

  return (
    <motion.div
      key={highlightKey}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="pointer-events-none absolute animate-pulse-highlight rounded-sm bg-yellow-400/50 ring-2 ring-yellow-400"
      style={{ left, top, width, height }}
    />
  );
}
