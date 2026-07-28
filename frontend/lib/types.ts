// Types mirroring the FastAPI backend schemas verbatim (see API contract in project spec).

// ---------- Auth ----------

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user: User;
}

export interface SignupRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ForgotPasswordResponse {
  message: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface ResetPasswordResponse {
  message: string;
}

// ---------- Documents ----------

export type DocumentStatus =
  | "queued"
  | "validating"
  | "extracting"
  | "ocr"
  | "chunking"
  | "embedding"
  | "done"
  | "failed";

export interface DocumentRead {
  id: string;
  filename: string;
  status: DocumentStatus;
  status_detail: string | null;
  progress_percent: number;
  page_count: number | null;
  chunk_count: number | null;
  embedding_count: number | null;
  processing_time_seconds: number | null;
  file_size_bytes: number;
  created_at: string;
}

export interface UploadResultItem {
  document: DocumentRead;
  duplicate_of: string | null;
}

// ---------- Chat ----------

export interface Citation {
  chunk_id: string;
  document_id: string;
  page_number: number;
  section_title: string | null;
  confidence_score: number;
  bbox: [number, number, number, number] | null;
}

export interface ConversationRead {
  id: string;
  title: string | null;
  document_ids: string[];
  created_at: string;
}

export type MessageRole = "user" | "assistant";

export interface MessageRead {
  id: string;
  role: MessageRole;
  content: string;
  confidence_score: number | null;
  created_at: string;
  citations: Citation[];
}

export interface CreateConversationRequest {
  document_ids: string[];
  title?: string;
}

export interface CreateMessageRequest {
  content: string;
}

// SSE stream event shapes for POST /conversations/{id}/messages
export interface ChatStreamTokenEvent {
  type: "token";
  content: string;
}

export interface ChatStreamDoneEvent {
  type: "done";
  message_id: string;
  confidence: number;
  citations: Citation[];
}

export type ChatStreamEvent = ChatStreamTokenEvent | ChatStreamDoneEvent;

// ---------- Dashboard ----------

export interface DashboardStats {
  total_documents: number;
  documents_processing: number;
  documents_done: number;
  documents_failed: number;
  total_pages: number;
  total_chunks: number;
  total_embeddings: number;
  storage_used_bytes: number;
  total_conversations: number;
}

export interface DashboardResponse {
  stats: DashboardStats;
  recent_documents: DocumentRead[];
  recent_conversations: ConversationRead[];
}

// ---------- Progress WebSocket ----------

export interface ProgressMessage {
  document_id: string;
  status: DocumentStatus;
  percent: number;
  detail: string | null;
}

// ---------- Errors ----------

export interface ApiErrorBody {
  detail?: string | { msg: string; [k: string]: unknown }[] | Record<string, unknown>;
}
