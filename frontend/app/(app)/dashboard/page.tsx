"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  FileText,
  Layers,
  Braces,
  HardDrive,
  MessagesSquare,
  FileCheck2,
  FileClock,
  FileWarning,
} from "lucide-react";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { UploadDropzone } from "@/components/upload/UploadDropzone";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { apiClient } from "@/lib/api-client";
import { formatBytes, formatDate } from "@/lib/utils";
import type { DashboardResponse } from "@/lib/types";

export default function DashboardPage() {
  const [data, setData] = React.useState<DashboardResponse | null>(null);
  const [loading, setLoading] = React.useState(true);

  const loadDashboard = React.useCallback(async () => {
    try {
      const res = await apiClient.get<DashboardResponse>("/dashboard/");
      setData(res);
    } catch (error) {
      toast.error((error as Error).message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const stats = data?.stats;

  const statCards = [
    { label: "Documents", value: stats?.total_documents, icon: FileText },
    { label: "Processing", value: stats?.documents_processing, icon: FileClock },
    { label: "Completed", value: stats?.documents_done, icon: FileCheck2 },
    { label: "Failed", value: stats?.documents_failed, icon: FileWarning },
    { label: "Pages", value: stats?.total_pages, icon: Layers },
    { label: "Chunks", value: stats?.total_chunks, icon: Braces },
    {
      label: "Storage used",
      value: stats ? formatBytes(stats.storage_used_bytes) : undefined,
      icon: HardDrive,
    },
    { label: "Conversations", value: stats?.total_conversations, icon: MessagesSquare },
  ];

  return (
    <div className="container space-y-8 py-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          An overview of your documents and conversations.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {statCards.map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: i * 0.03 }}
          >
            <Card>
              <CardContent className="flex items-center justify-between p-4">
                <div>
                  <p className="text-xs text-muted-foreground">{card.label}</p>
                  {loading ? (
                    <Skeleton className="mt-1 h-6 w-12" />
                  ) : (
                    <p className="text-xl font-semibold">{card.value ?? 0}</p>
                  )}
                </div>
                <card.icon className="h-5 w-5 text-muted-foreground" />
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Upload documents</CardTitle>
            <CardDescription>Drag and drop PDFs, or click to browse.</CardDescription>
          </CardHeader>
          <CardContent>
            <UploadDropzone onDocumentReady={() => void loadDashboard()} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent documents</CardTitle>
            <CardDescription>Your most recently uploaded files.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : !data?.recent_documents.length ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No documents yet. Upload a PDF to get started.
              </p>
            ) : (
              <ul className="space-y-1">
                {data.recent_documents.map((doc) => (
                  <li key={doc.id}>
                    <Link
                      href={`/documents/${doc.id}`}
                      className="flex items-center justify-between gap-3 rounded-md px-2 py-2 text-sm hover:bg-accent"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{doc.filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(doc.created_at)} · {formatBytes(doc.file_size_bytes)}
                        </p>
                      </div>
                      <StatusBadge status={doc.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent conversations</CardTitle>
          <CardDescription>Jump back into a previous chat.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !data?.recent_conversations.length ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No conversations yet. Open a document to start chatting.
            </p>
          ) : (
            <ul className="space-y-1">
              {data.recent_conversations.map((conv) => {
                const firstDocId = conv.document_ids[0];
                return (
                  <li key={conv.id}>
                    <Link
                      href={firstDocId ? `/documents/${firstDocId}` : "/dashboard"}
                      className="flex items-center justify-between gap-3 rounded-md px-2 py-2 text-sm hover:bg-accent"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">
                          {conv.title || `Conversation (${conv.document_ids.length} doc${conv.document_ids.length > 1 ? "s" : ""})`}
                        </p>
                        <p className="text-xs text-muted-foreground">{formatDate(conv.created_at)}</p>
                      </div>
                      <MessagesSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
