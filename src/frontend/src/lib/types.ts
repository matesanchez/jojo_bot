export interface Citation {
  document: string;
  section: string;
  page?: number;
  excerpt: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  timestamp: string;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  citations: Citation[];
  follow_up_suggestions: string[];
  instrument_detected?: string;
}

export interface Session {
  id: string;
  title: string;
  instrument_context?: string;
  created_at: string;
  last_active: string;
}

export interface ProtocolRequest {
  target_protein: string;
  purification_type: string;
  instrument: string;
  column?: string;
  sample_volume?: string;
  additional_notes?: string;
  session_id?: string;
}

export interface ProtocolResponse {
  protocol_markdown: string;
  protocol_title: string;
  warnings: string[];
  session_id: string;
}

// Settings & knowledge base types
export interface ApiKeyStatus {
  configured: boolean;
  masked_key: string | null;
}

export interface KbDocument {
  source_file: string;
  doc_title: string;
  instruments: string[];
  chunk_count: number;
  page_count: number;
  category: "base" | "user";
  added_at: string;
}

export interface KbListResponse {
  documents: KbDocument[];
  total: number;
}

export type IngestEvent =
  | { type: "start"; total: number }
  | { type: "progress"; current: number; total: number; filename: string; chunks_added: number }
  | { type: "done"; chunks_added: number; files_processed: number; errors: string[] }
  | { type: "error"; message: string };
