import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/lib/types";

const STATUS_VARIANT: Record<DocumentStatus, "default" | "secondary" | "destructive" | "success" | "outline"> = {
  queued: "secondary",
  validating: "secondary",
  extracting: "outline",
  ocr: "outline",
  chunking: "outline",
  embedding: "outline",
  done: "success",
  failed: "destructive",
};

const STATUS_LABEL: Record<DocumentStatus, string> = {
  queued: "Queued",
  validating: "Validating",
  extracting: "Extracting",
  ocr: "OCR",
  chunking: "Chunking",
  embedding: "Embedding",
  done: "Done",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}
