"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, UploadCloud, X, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { cn, formatBytes } from "@/lib/utils";
import { apiUrl } from "@/lib/api-client";
import { getAccessToken } from "@/store/auth-store";
import { useProgressWs } from "@/lib/use-progress-ws";
import type { DocumentRead, DocumentStatus, UploadResultItem } from "@/lib/types";

interface UploadItem {
  key: string;
  file: File;
  uploadProgress: number; // 0-100
  phase: "uploading" | "processing" | "done" | "error" | "duplicate";
  document?: DocumentRead;
  error?: string;
}

const STATUS_LABELS: Record<DocumentStatus, string> = {
  queued: "Queued",
  validating: "Validating",
  extracting: "Extracting text",
  ocr: "Running OCR",
  chunking: "Chunking",
  embedding: "Embedding",
  done: "Done",
  failed: "Failed",
};

function uploadFile(file: File): Promise<{ status: number; body: UploadResultItem[] | { detail?: string } }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl("/documents/upload"));
    const token = getAccessToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgressMap.get(file)?.(percent);
      }
    };

    xhr.onload = () => {
      let body: UploadResultItem[] | { detail?: string } = {};
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        body = {};
      }
      resolve({ status: xhr.status, body });
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));

    const formData = new FormData();
    formData.append("files", file);
    xhr.send(formData);
  });
}

// Simple side-channel to report progress from the XHR callback back to React state
const onProgressMap = new Map<File, (percent: number) => void>();

interface UploadDropzoneProps {
  onDocumentReady?: (document: DocumentRead) => void;
}

export function UploadDropzone({ onDocumentReady }: UploadDropzoneProps) {
  const [items, setItems] = React.useState<UploadItem[]>([]);
  const [isDragging, setIsDragging] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  function updateItem(key: string, patch: Partial<UploadItem>) {
    setItems((prev) => prev.map((it) => (it.key === key ? { ...it, ...patch } : it)));
  }

  async function handleFiles(files: FileList | File[]) {
    const fileArray = Array.from(files).filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
    if (fileArray.length === 0) {
      toast.error("Only PDF files are supported");
      return;
    }

    const newItems: UploadItem[] = fileArray.map((file) => ({
      key: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
      file,
      uploadProgress: 0,
      phase: "uploading",
    }));

    setItems((prev) => [...newItems, ...prev]);

    for (const item of newItems) {
      onProgressMap.set(item.file, (percent) => updateItem(item.key, { uploadProgress: percent }));

      try {
        const { status, body } = await uploadFile(item.file);
        onProgressMap.delete(item.file);

        if (status !== 201 || !Array.isArray(body)) {
          const detail = !Array.isArray(body) && body?.detail ? String(body.detail) : "Upload failed";
          updateItem(item.key, { phase: "error", error: detail });
          toast.error(`${item.file.name}: ${detail}`);
          continue;
        }

        const result = body[0];
        if (!result) {
          updateItem(item.key, { phase: "error", error: "No document returned" });
          continue;
        }

        if (result.duplicate_of) {
          updateItem(item.key, { phase: "duplicate", document: result.document });
          toast.info("This file was already uploaded");
          continue;
        }

        updateItem(item.key, {
          phase: result.document.status === "done" ? "done" : "processing",
          document: result.document,
          uploadProgress: 100,
        });
        if (result.document.status === "done") {
          onDocumentReady?.(result.document);
        }
      } catch (error) {
        onProgressMap.delete(item.file);
        updateItem(item.key, { phase: "error", error: (error as Error).message });
        toast.error(`${item.file.name}: ${(error as Error).message}`);
      }
    }
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) {
      void handleFiles(e.dataTransfer.files);
    }
  }

  function removeItem(key: string) {
    setItems((prev) => prev.filter((it) => it.key !== key));
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors",
          isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50"
        )}
      >
        <UploadCloud className="mb-3 h-8 w-8 text-muted-foreground" />
        <p className="text-sm font-medium">Drag &amp; drop PDF files here, or click to browse</p>
        <p className="mt-1 text-xs text-muted-foreground">Supports multiple files</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) void handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <AnimatePresence initial={false}>
        {items.map((item) => (
          <UploadItemRow
            key={item.key}
            item={item}
            onRemove={() => removeItem(item.key)}
            onProcessingDone={(finalStatus) => {
              updateItem(item.key, { phase: finalStatus === "done" ? "done" : "error" });
              if (finalStatus === "done" && item.document) {
                onDocumentReady?.({ ...item.document, status: "done" });
              }
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

function UploadItemRow({
  item,
  onRemove,
  onProcessingDone,
}: {
  item: UploadItem;
  onRemove: () => void;
  onProcessingDone: (finalStatus: DocumentStatus) => void;
}) {
  const documentId = item.phase === "processing" ? item.document?.id ?? null : null;
  const { progress } = useProgressWs(documentId, {
    enabled: item.phase === "processing",
    onDone: (message) => onProcessingDone(message.status),
  });

  const status = progress?.status ?? item.document?.status;
  const percent = item.phase === "uploading" ? item.uploadProgress : progress?.percent ?? item.document?.progress_percent ?? 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="flex items-center gap-3 rounded-md border p-3"
    >
      <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm font-medium">{item.file.name}</p>
          <span className="text-xs text-muted-foreground">{formatBytes(item.file.size)}</span>
        </div>
        {item.phase === "uploading" && (
          <div className="mt-1.5 space-y-1">
            <Progress value={item.uploadProgress} className="h-1.5" />
            <p className="text-xs text-muted-foreground">Uploading… {item.uploadProgress}%</p>
          </div>
        )}
        {item.phase === "processing" && (
          <div className="mt-1.5 space-y-1">
            <Progress value={percent} className="h-1.5" />
            <p className="text-xs text-muted-foreground">
              {status ? STATUS_LABELS[status] : "Processing"}
              {progress?.detail ? ` · ${progress.detail}` : ""} ({percent}%)
            </p>
          </div>
        )}
        {item.phase === "done" && (
          <p className="mt-1 flex items-center gap-1 text-xs text-success">
            <CheckCircle2 className="h-3.5 w-3.5" /> Ready
          </p>
        )}
        {item.phase === "duplicate" && (
          <p className="mt-1 text-xs text-muted-foreground">Already uploaded previously</p>
        )}
        {item.phase === "error" && (
          <p className="mt-1 flex items-center gap-1 text-xs text-destructive">
            <XCircle className="h-3.5 w-3.5" /> {item.error || "Upload failed"}
          </p>
        )}
      </div>
      <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={onRemove}>
        <X className="h-3.5 w-3.5" />
      </Button>
    </motion.div>
  );
}
