"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { deleteSession, getSession, getSessions, sendMessage } from "@/lib/api";
import { Message, Session } from "@/lib/types";
import Header from "@/components/Header";
import ChatWindow from "@/components/ChatWindow";
import InputArea from "@/components/InputArea";
import SessionSidebar from "@/components/SessionSidebar";
import ProtocolDialog from "@/components/ProtocolDialog";

const PROTOCOL_KEYWORDS = ["generate protocol", "write a protocol", "purification protocol", "create a protocol", "generate a protocol for"];

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [instrumentFilter, setInstrumentFilter] = useState("");
  const [followUps, setFollowUps] = useState<string[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [protocolOpen, setProtocolOpen] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [instrumentNotice, setInstrumentNotice] = useState("");
  const prevInstrument = useRef(instrumentFilter);

  // Load sessions on mount
  useEffect(() => {
    getSessions()
      .then(setSessions)
      .catch(() => {});
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
      // Check for protocol keywords
      if (PROTOCOL_KEYWORDS.some((kw) => text.toLowerCase().includes(kw))) {
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
        getSessions().then(setSessions).catch(() => {});
      } catch (e: unknown) {
        setConnectionError(true);
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
        timestamp: m.created_at || new Date().toISOString(),
      }));
      setMessages(msgs);
      setSessionId(id);
      setSidebarOpen(false);
    } catch {}
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (sessionId === id) handleNewChat();
    } catch {}
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
          onQuickAction={handleSend}
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
    </div>
  );
}
