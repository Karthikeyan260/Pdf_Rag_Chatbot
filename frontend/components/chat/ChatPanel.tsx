"use client";

import * as React from "react";
import { Send, Loader2, MessagesSquare, FilePlus2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { apiClient } from "@/lib/api-client";
import { useChatStream } from "@/lib/use-chat-stream";
import { useChatStore } from "@/store/chat-store";
import type { Citation, ConversationRead, DocumentRead, MessageRead } from "@/lib/types";

interface ChatPanelProps {
  documentId: string;
  onCitationClick?: (citation: Citation) => void;
}

function tempId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function ChatPanel({ documentId, onCitationClick }: ChatPanelProps) {
  const conversations = useChatStore((s) => s.conversations);
  const setConversations = useChatStore((s) => s.setConversations);
  const upsertConversation = useChatStore((s) => s.upsertConversation);
  const messagesByConversation = useChatStore((s) => s.messagesByConversation);
  const setMessages = useChatStore((s) => s.setMessages);
  const appendMessage = useChatStore((s) => s.appendMessage);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const setActiveConversationId = useChatStore((s) => s.setActiveConversationId);

  const [allDocuments, setAllDocuments] = React.useState<DocumentRead[]>([]);
  const [pickerSelectedIds, setPickerSelectedIds] = React.useState<string[]>([documentId]);
  const [loadingInitial, setLoadingInitial] = React.useState(true);
  const [input, setInput] = React.useState("");
  const [starting, setStarting] = React.useState(false);

  const { isStreaming, sendMessage } = useChatStream();
  const streamContentRef = React.useRef("");
  const [liveContent, setLiveContent] = React.useState("");
  const scrollBottomRef = React.useRef<HTMLDivElement>(null);

  const activeConversation = conversations.find((c) => c.id === activeConversationId) || null;
  const messages = activeConversationId ? messagesByConversation[activeConversationId] ?? [] : [];

  // Initial load: documents (for the picker) + conversations, then pick the
  // most relevant existing conversation for this document, if any.
  React.useEffect(() => {
    let cancelled = false;
    setActiveConversationId(null);
    setPickerSelectedIds([documentId]);

    async function init() {
      setLoadingInitial(true);
      try {
        const [docs, convos] = await Promise.all([
          apiClient.get<DocumentRead[]>("/documents/"),
          apiClient.get<ConversationRead[]>("/chat/conversations"),
        ]);
        if (cancelled) return;
        setAllDocuments(docs);
        setConversations(convos);

        const match = convos.find((c) => c.document_ids.includes(documentId));
        if (match) {
          setActiveConversationId(match.id);
          const msgs = await apiClient.get<MessageRead[]>(
            `/chat/conversations/${match.id}/messages`
          );
          if (cancelled) return;
          setMessages(match.id, msgs);
        }
      } catch (error) {
        if (!cancelled) toast.error((error as Error).message || "Failed to load conversations");
      } finally {
        if (!cancelled) setLoadingInitial(false);
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  React.useEffect(() => {
    scrollBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, liveContent]);

  function toggleDocSelection(id: string) {
    setPickerSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  }

  async function startConversation() {
    if (pickerSelectedIds.length === 0) {
      toast.error("Select at least one document");
      return;
    }
    setStarting(true);
    try {
      const conversation = await apiClient.post<ConversationRead>("/chat/conversations", {
        document_ids: pickerSelectedIds,
      });
      upsertConversation(conversation);
      setMessages(conversation.id, []);
      setActiveConversationId(conversation.id);
    } catch (error) {
      toast.error((error as Error).message || "Failed to start conversation");
    } finally {
      setStarting(false);
    }
  }

  async function handleSend() {
    const content = input.trim();
    if (!content || !activeConversationId || isStreaming) return;

    const userMessage: MessageRead = {
      id: tempId("user"),
      role: "user",
      content,
      confidence_score: null,
      created_at: new Date().toISOString(),
      citations: [],
    };
    appendMessage(activeConversationId, userMessage);
    setInput("");
    streamContentRef.current = "";
    setLiveContent("");

    await sendMessage(activeConversationId, content, {
      onToken: (contentSoFar) => {
        streamContentRef.current = contentSoFar;
        setLiveContent(contentSoFar);
      },
      onDone: (result) => {
        const assistantMessage: MessageRead = {
          id: result.messageId,
          role: "assistant",
          content: streamContentRef.current,
          confidence_score: result.confidence,
          created_at: new Date().toISOString(),
          citations: result.citations,
        };
        appendMessage(activeConversationId, assistantMessage);
        setLiveContent("");
        streamContentRef.current = "";
      },
      onError: (error) => {
        toast.error(error.message || "Chat stream failed");
        setLiveContent("");
      },
    });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void handleSend();
    }
  }

  if (loadingInitial) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  if (!activeConversationId) {
    return (
      <div className="flex h-full flex-col gap-4 p-4">
        <div className="flex items-center gap-2 text-sm font-medium">
          <FilePlus2 className="h-4 w-4" />
          Start a conversation
        </div>
        <p className="text-xs text-muted-foreground">
          Choose one or more documents to chat with. Select more than one to ask questions across
          multiple PDFs at once.
        </p>
        <div className="flex-1 space-y-1 overflow-auto rounded-md border p-2">
          {allDocuments.length === 0 && (
            <p className="p-2 text-xs text-muted-foreground">No documents uploaded yet.</p>
          )}
          {allDocuments.map((doc) => (
            <label
              key={doc.id}
              className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
            >
              <Checkbox
                checked={pickerSelectedIds.includes(doc.id)}
                onCheckedChange={() => toggleDocSelection(doc.id)}
              />
              <span className="truncate">{doc.filename}</span>
            </label>
          ))}
        </div>
        <Button onClick={startConversation} disabled={starting}>
          {starting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Start conversation
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b px-4 py-2.5 text-sm text-muted-foreground">
        <MessagesSquare className="h-4 w-4" />
        <span>
          {activeConversation?.document_ids.length ?? 1} document
          {(activeConversation?.document_ids.length ?? 1) > 1 ? "s" : ""} in this conversation
        </span>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-4 p-4">
          {messages.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Ask a question about this document to get started.
            </p>
          )}
          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              role={m.role}
              content={m.content}
              citations={m.citations}
              confidence={m.confidence_score}
              onCitationClick={onCitationClick}
            />
          ))}
          {isStreaming && (
            <MessageBubble role="assistant" content={liveContent} isStreaming />
          )}
          <div ref={scrollBottomRef} />
        </div>
      </ScrollArea>

      <div className="border-t p-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question… (Ctrl/Cmd+Enter to send)"
            rows={2}
            className="flex-1 resize-none rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
          <Button onClick={() => void handleSend()} disabled={isStreaming || !input.trim()} size="icon">
            {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
