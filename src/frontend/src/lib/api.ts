import {
  ApiKeyStatus,
  ChatResponse,
  IngestEvent,
  KbListResponse,
  Message,
  ProtocolRequest,
  ProtocolResponse,
  Session,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SAFE_ERROR_PATTERN = /^[\w\s.,!?:()\-']{0,200}$/;

/** Create an AbortSignal that fires after `ms` milliseconds. */
function timeoutSignal(ms: number): AbortSignal {
  const controller = new AbortController();
  setTimeout(() => controller.abort(), ms);
  return controller.signal;
}

// Default timeouts (milliseconds)
const DEFAULT_TIMEOUT = 30_000;   // 30 s for normal requests
const CHAT_TIMEOUT = 120_000;     // 2 min for chat (Claude API can be slow)
const UPLOAD_TIMEOUT = 300_000;   // 5 min for uploads (large PDF ingestion)

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed (HTTP ${res.status})`;
    try {
      const body = await res.json();
      const detail = typeof body?.detail === "string" ? body.detail : "";
      if (detail && SAFE_ERROR_PATTERN.test(detail)) {
        message = detail;
      }
    } catch {
      // Ignore JSON parse failures
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export async function sendMessage(
  message: string,
  sessionId: string | null,
  instrumentFilter: string | null
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      instrument_filter: instrumentFilter,
    }),
    signal: timeoutSignal(CHAT_TIMEOUT),
  });
  return handleResponse<ChatResponse>(res);
}

export async function getSessions(): Promise<Session[]> {
  const res = await fetch(`${API_URL}/api/sessions`, { signal: timeoutSignal(DEFAULT_TIMEOUT) });
  return handleResponse<Session[]>(res);
}

export async function getSession(
  id: string
): Promise<{ session_id: string; session: Session; messages: Message[] }> {
  const res = await fetch(`${API_URL}/api/sessions/${id}`, { signal: timeoutSignal(DEFAULT_TIMEOUT) });
  return handleResponse<{ session_id: string; session: Session; messages: Message[] }>(res);
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/sessions/${id}`, { method: "DELETE", signal: timeoutSignal(DEFAULT_TIMEOUT) });
  await handleResponse<void>(res);
}

export async function generateProtocol(
  request: ProtocolRequest
): Promise<ProtocolResponse> {
  const res = await fetch(`${API_URL}/api/generate-protocol`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: timeoutSignal(CHAT_TIMEOUT),
  });
  return handleResponse<ProtocolResponse>(res);
}

// ---------------------------------------------------------------------------
// Settings — API key
// ---------------------------------------------------------------------------

export async function getApiKeyStatus(): Promise<ApiKeyStatus> {
  const res = await fetch(`${API_URL}/api/settings/api-key`, { signal: timeoutSignal(DEFAULT_TIMEOUT) });
  return handleResponse<ApiKeyStatus>(res);
}

export async function saveApiKey(apiKey: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/settings/api-key`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey }),
    signal: timeoutSignal(DEFAULT_TIMEOUT),
  });
  await handleResponse<{ status: string }>(res);
}

export async function deleteApiKey(): Promise<void> {
  const res = await fetch(`${API_URL}/api/settings/api-key`, { method: "DELETE", signal: timeoutSignal(DEFAULT_TIMEOUT) });
  await handleResponse<{ status: string }>(res);
}

// ---------------------------------------------------------------------------
// Knowledge base
// ---------------------------------------------------------------------------

export async function getKnowledgeBase(): Promise<KbListResponse> {
  const res = await fetch(`${API_URL}/api/knowledge-base`, { signal: timeoutSignal(DEFAULT_TIMEOUT) });
  return handleResponse<KbListResponse>(res);
}

export async function deleteKbDocument(sourceFile: string): Promise<void> {
  const res = await fetch(
    `${API_URL}/api/knowledge-base/${encodeURIComponent(sourceFile)}`,
    { method: "DELETE", signal: timeoutSignal(DEFAULT_TIMEOUT) }
  );
  await handleResponse<{ status: string }>(res);
}

/**
 * Upload PDF files to the knowledge base.
 * Returns an async generator that yields IngestEvent objects streamed via SSE.
 */
export async function* uploadDocuments(
  files: File[],
  instrument: string
): AsyncGenerator<IngestEvent> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  formData.append("instrument", instrument);

  const res = await fetch(`${API_URL}/api/knowledge-base/upload`, {
    method: "POST",
    body: formData,
    signal: timeoutSignal(UPLOAD_TIMEOUT),
  });

  if (!res.ok) {
    let msg = `Upload failed (HTTP ${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") msg = body.detail;
    } catch {}
    throw new Error(msg);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE messages are separated by double newline
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      for (const line of part.split("\n")) {
        if (line.startsWith("data: ")) {
          try {
            const event = JSON.parse(line.slice(6)) as IngestEvent;
            yield event;
          } catch {
            // Malformed SSE line — skip
          }
        }
      }
    }
  }
}
