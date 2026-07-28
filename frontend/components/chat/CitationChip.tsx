"use client";

import { FileText } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Citation } from "@/lib/types";

interface CitationChipProps {
  citation: Citation;
  onClick?: (citation: Citation) => void;
}

export function CitationChip({ citation, onClick }: CitationChipProps) {
  const confidencePercent = Math.round(citation.confidence_score * 100);

  return (
    <button
      type="button"
      onClick={() => onClick?.(citation)}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/60 px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:bg-primary/10 hover:text-foreground"
      )}
    >
      <FileText className="h-3 w-3" />
      <span>
        Page {citation.page_number}
        {citation.section_title ? ` · ${citation.section_title}` : ""} · {confidencePercent}%
      </span>
    </button>
  );
}
