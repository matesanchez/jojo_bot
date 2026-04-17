"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { deleteSession, getApiKeyStatus, getSession, getSessions, sendMessage } from "@/lib/api";
import { Message, Session } from "@/lib/types";
import Header from "@/components/Header";
import ChatWindow from "@/components/ChatWindow";
import InputArea from "@/components/InputArea";
import SessionSidebar from "@/components/SessionSidebar";
import ProtocolDialog from "@/components/ProtocolDialog";
import SettingsPanel from "@/components/SettingsPanel";

// Word-boundary regex prevents false positives like "protocolize" or "ungenerated protocol"
const PROTOCOL_TRIGGER = /\b(generate|write|create|make)\s+(a\s+)?(purification\s+)?protocol\b/i;

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [instrumentFilter, setInstrumentFilter] = useState("");
  const [followUps, setFollowUps] = useState<string[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [protocolOpen, setProtocolOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [instrumentNotice, setInstrumentNotice] = useState("");
  const [apiKeyConfigured, setApiKeyConfigured] = useState(true); // optimistic
  const prevInstrument = useRef(instrumentFilter);

  // Load sessions and check API key status on mount
  useEffect(() => {
    getSessions()
      .then(setSessions)
      .catch((e) => console.error("Failed to load sessions:", e));

    getApiKeyStatus()
      .then((status) => setApiKeyConfigured(status.configured))
      .catch(() => setApiKeyConfigured(false));
  }, []);

  // Show notice when instrument filter changes
  useEffect(() => {
    if (prevInstrument.current !== instrumentFilter) {
      prevInstrument.current = instrumentFilter;
      if (instrumentFilter) {
        const label = instrumentFilter.replace("_", " ");
        setInstrumentNotice(`Filtering to ÄKTA ${label} documents`);
        const t = setTimeout(() => setInstrumentNotice(""), 3000);
        return () => clearTimeout(t);
      }
    }
  }, [instrumentFilter]);

  const handleSend = useCallback(
    async (text: string) => {
      // Check for protocol trigger (word-boundary regex)
      if (PROTOCOL_TRIGGER.test(text)) {
        setProtocolOpen(true);
        return;
      }

      const userMsg: Message = {
        id: uuidv4(),
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setFollowUps([]);
      setConnectionError(false);

      try {
        const res = await sendMessage(text, sessionId, instrumentFilter || null);

        if (!sessionId) {
          setSessionId(res.session_id);
        }

        const assistantMsg: Message = {
          id: uuidv4(),
          role: "assistant",
          content: res.response,
          citations: res.citations,
          timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
        setFollowUps(res.follow_up_suggestions || []);

        // Refresh sessions list
        getSessions().then(setSessions).catch((e) => console.error("Failed to refresh sessions:", e));
      } catch (e: unknown) {
        setConnectionError(true);
        console.error("Chat request failed:", e instanceof Error ? e.message : e);
        const errorMsg: Message = {
          id: uuidv4(),
          role: "assistant",
          content: "Jojo Bot is taking a nap. Make sure the backend server is running on port 8000.",
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, instrumentFilter]
  );

  const handleNewChat = () => {
    setMessages([]);
    setSessionId(null);
    setFollowUps([]);
    setConnectionError(false);
    setSidebarOpen(false);
  };

  const handleSelectSession = async (id: string) => {
    try {
      const data = await getSession(id);
      const msgs: Message[] = data.messages.map((m) => ({
        id: m.id || uuidv4(),
        role: m.role,
        content: m.content,
        citations: m.citations,
        timestamp: m.timestamp || (m as any).created_at || new Date().toISOString(),
      }));
      setMessages(msgs);
      setSessionId(id);
      setSidebarOpen(false);
    } catch (e: unknown) {
      console.error("Failed to load session:", e instanceof Error ? e.message : e);
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (sessionId === id) handleNewChat();
    } catch (e: unknown) {
      console.error("Failed to delete session:", e instanceof Error ? e.message : e);
    }
  };

  const handleApiKeyChange = (configured: boolean) => {
    setApiKeyConfigured(configured);
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <SessionSidebar
        sessions={sessions}
        currentSessionId={sessionId}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onNewChat={handleNewChat}
      />

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        <Header
          instrumentFilter={instrumentFilter}
          onInstrumentChange={setInstrumentFilter}
          onNewChat={handleNewChat}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          onOpenSettings={() => setSettingsOpen(true)}
          apiKeyConfigured={apiKeyConfigured}
        />

        {/* Connection error banner */}
        {connectionError && (
          <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-sm text-red-700 text-center">
            ⚠️ Cannot reach the backend server. Make sure it&apos;s running on port 8000.
          </div>
        )}

        {/* Instrument filter notice */}
        {instrumentNotice && (
          <div className="bg-emerald-50 border-b border-emerald-100 px-4 py-2 text-sm text-emerald-700 text-center transition-all">
            🔍 {instrumentNotice}
          </div>
        )}

        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          apiKeyConfigured={apiKeyConfigured}
          onQuickAction={handleSend}
          onOpenSettings={() => setSettingsOpen(true)}
        />

        <InputArea
          onSend={handleSend}
          isLoading={isLoading}
          followUpSuggestions={followUps}
        />
      </div>

      {/* Protocol dialog */}
      <ProtocolDialog
        isOpen={protocolOpen}
        onClose={() => setProtocolOpen(false)}
        sessionId={sessionId}
      />

      {/* Settings panel */}
      <SettingsPanel
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onApiKeyChange={handleApiKeyChange}
      />
    </div>
  );
}
