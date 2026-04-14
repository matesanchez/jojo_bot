import { ChatResponse, Message, ProtocolRequest, ProtocolResponse, Session } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch {}
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

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
  });
  return handleResponse<ChatResponse>(res);
}

export async function getSessions(): Promise<Session[]> {
  const res = await fetch(`${API_URL}/api/sessions`);
  return handleResponse<Session[]>(res);
}

export async function getSession(
  id: string
): Promise<{ session_id: string; session: Session; messages: Message[] }> {
  const res = await fetch(`${API_URL}/api/sessions/${id}`);
  return handleResponse<{ session_id: string; session: Session; messages: Message[] }>(res);
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/sessions/${id}`, { method: "DELETE" });
  await handleResponse<void>(res);
}

export async function generateProtocol(
  request: ProtocolRequest
): Promise<ProtocolResponse> {
  const res = await fetch(`${API_URL}/api/generate-protocol`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handleResponse<ProtocolResponse>(res);
}
