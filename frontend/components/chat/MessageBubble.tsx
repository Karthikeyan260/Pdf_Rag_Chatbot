"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { User, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import { CitationChip } from "@/components/chat/CitationChip";
import type { Citation, MessageRole } from "@/lib/types";

interface MessageBubbleProps {
  role: MessageRole;
  content: string;
  citations?: Citation[];
  confidence?: number | null;
  isStreaming?: boolean;
  onCitationClick?: (citation: Citation) => void;
}

export function MessageBubble({
  role,
  content,
  citations,
  confidence,
  isStreaming,
  onCitationClick,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={cn("flex gap-3", isUser && "flex-row-reverse")}
    >
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
      </div>

      <div className={cn("min-w-0 max-w-[85%] space-y-2", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "rounded-tr-sm bg-primary text-primary-foreground"
              : "rounded-tl-sm bg-muted text-foreground"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{content}</p>
          ) : (
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {content || (isStreaming ? "" : "")}
              </ReactMarkdown>
              {isStreaming && (
                <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-current align-middle" />
              )}
            </div>
          )}
        </div>

        {!isUser && typeof confidence === "number" && (
          <p className="px-1 text-xs text-muted-foreground">
            Confidence: {Math.round(confidence * 100)}%
          </p>
        )}

        {!isUser && citations && citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {citations.map((c) => (
              <CitationChip key={c.chunk_id} citation={c} onClick={onCitationClick} />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

const markdownComponents = {
  table: ({ ...props }: React.ComponentPropsWithoutRef<"table">) => (
    <div className="my-2 overflow-x-auto rounded-md border">
      <table className="w-full border-collapse text-xs" {...props} />
    </div>
  ),
  th: ({ ...props }: React.ComponentPropsWithoutRef<"th">) => (
    <th className="border-b bg-muted/60 px-2 py-1.5 text-left font-semibold" {...props} />
  ),
  td: ({ ...props }: React.ComponentPropsWithoutRef<"td">) => (
    <td className="border-b px-2 py-1.5 align-top" {...props} />
  ),
  code: ({ className, children, ...props }: React.ComponentPropsWithoutRef<"code">) => {
    const isBlock = /language-/.test(className || "");
    if (isBlock) {
      return (
        <code className={cn("block overflow-x-auto rounded-md bg-black/80 p-3 text-xs text-white", className)} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="rounded bg-black/10 px-1 py-0.5 text-[0.85em] dark:bg-white/10" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ ...props }: React.ComponentPropsWithoutRef<"pre">) => (
    <pre className="my-2 overflow-x-auto rounded-md" {...props} />
  ),
  a: ({ ...props }: React.ComponentPropsWithoutRef<"a">) => (
    <a className="text-primary underline underline-offset-2" target="_blank" rel="noreferrer" {...props} />
  ),
  ul: ({ ...props }: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="my-1 list-disc pl-5" {...props} />
  ),
  ol: ({ ...props }: React.ComponentPropsWithoutRef<"ol">) => (
    <ol className="my-1 list-decimal pl-5" {...props} />
  ),
  p: ({ ...props }: React.ComponentPropsWithoutRef<"p">) => (
    <p className="mb-1.5 last:mb-0" {...props} />
  ),
};
