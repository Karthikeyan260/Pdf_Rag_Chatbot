# API Reference

Base URL: `http://localhost:8000/api/v1` (interactive Swagger UI at `http://localhost:8000/docs`, raw OpenAPI JSON at `/api/openapi.json`).

All endpoints except `auth/signup`, `auth/login`, `auth/forgot-password`, `auth/reset-password`, and `/health` require `Authorization: Bearer <access_token>`.

## Auth

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/auth/signup` | `{email, password, full_name?}` | `201` `TokenResponse` |
| POST | `/auth/login` | `{email, password}` | `200` `TokenResponse` / `401` |
| POST | `/auth/forgot-password` | `{email}` | `202` always (no account enumeration) — logs a reset token server-side; wiring an email provider is a Phase 2 task |
| POST | `/auth/reset-password` | `{token, new_password}` | `200` / `400` if token invalid/expired |
| GET | `/auth/me` | — | `200` `UserRead` |

`TokenResponse = {access_token, refresh_token, token_type: "bearer", user: UserRead}`
`UserRead = {id, email, full_name, is_active}`

Access tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 24h); there is no `/auth/refresh` endpoint in Phase 1 — re-login once the access token expires (refresh-token rotation is a Phase 2 task).

## Documents

| Method | Path | Notes |
|---|---|---|
| POST | `/documents/upload` | `multipart/form-data`, repeat the `files` field per PDF. Returns `201` array of `{document: DocumentRead, duplicate_of: uuid \| null}` — one entry per uploaded file, in order. If `duplicate_of` is set (matched by SHA-256 of file contents for this user), no new row/processing job was created. |
| GET | `/documents` | List the caller's documents, newest first. |
| GET | `/documents/{id}` | Single document; `404` if not owned. |
| GET | `/documents/{id}/file` | Raw PDF bytes (`application/pdf`) — used as the `file` source for the PDF viewer. |
| DELETE | `/documents/{id}` | `204`. Deletes the DB row (cascades to chunks/citations) and the document's vectors; does not currently delete the file from disk. |

`DocumentRead = {id, filename, status, status_detail, progress_percent, page_count, chunk_count, embedding_count, processing_time_seconds, file_size_bytes, created_at}`

`status` moves through: `queued → validating → extracting → [ocr] → extracting → chunking → embedding → done`, or `failed` at any point (`status_detail` carries the error message).

## Chat

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/chat/conversations` | `{document_ids: uuid[], title?}` | Creates a conversation scoped to one or more documents (multi-PDF chat). `404` if any document isn't owned by the caller. |
| GET | `/chat/conversations` | — | List the caller's conversations, newest first. |
| GET | `/chat/conversations/{id}/messages` | — | Full message history with citations. |
| POST | `/chat/conversations/{id}/messages` | `{content}` | **Server-Sent Events** stream (`text/event-stream`), not JSON. See below. |

`ConversationRead = {id, title, document_ids, created_at}`
`MessageRead = {id, role: "user"|"assistant", content, confidence_score, created_at, citations: Citation[]}`
`Citation = {chunk_id, document_id, page_number, section_title, confidence_score, bbox}` — `bbox` is `[x0, y0, x1, y1]` in PDF point space (72dpi, top-left origin), or `null` for a chunk without page-position data (rare).

### Streaming chat protocol

The response body is a stream of `data: <json>\n\n` lines (standard SSE framing). Two event shapes:

```
data: {"type": "token", "content": "Revenue grew "}
data: {"type": "token", "content": "12% year over year"}
...
data: {"type": "done", "message_id": "…", "confidence": 0.83, "citations": [Citation, ...]}
```

Concatenate `token.content` in order to build the assistant message; the `done` event carries the persisted `message_id`, an overall confidence score (mean of the reranker scores of the chunks actually used), and the citation list. Because this is a POST with an auth header and a body, use `fetch` + a `ReadableStream` reader rather than the browser `EventSource` API (which only supports GET, no custom headers).

## Dashboard

| Method | Path |
|---|---|
| GET | `/dashboard` |

Returns `{stats: {total_documents, documents_processing, documents_done, documents_failed, total_pages, total_chunks, total_embeddings, storage_used_bytes, total_conversations}, recent_documents: DocumentRead[], recent_conversations: ConversationRead[]}`.

## Processing progress (WebSocket)

```
ws(s)://<host>/api/v1/ws/documents/{document_id}/progress?token=<access_token>
```

Pushes `{"document_id", "status", "percent", "detail"}` JSON messages as the document moves through the pipeline (same `status` enum as `DocumentRead.status`); the server closes the socket once `status` is `done` or `failed`. Auth is passed as a query param here (not a header) since the WebSocket handshake is a browser-initiated GET without custom-header support.

## Error shape

FastAPI's default: `{"detail": "<message>"}` with the appropriate 4xx/5xx status code. Validation errors (`422`) use the standard FastAPI/Pydantic `{"detail": [{"loc", "msg", "type"}, ...]}` array shape.
