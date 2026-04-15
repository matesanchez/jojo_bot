"use client";

import { PlusCircle, Trash2, X } from "lucide-react";
import { Session } from "@/lib/types";

interface Props {
  sessions: Session[];
  currentSessionId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onNewChat: () => void;
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / 86400000);
    if (diff === 0) return "Today";
    if (diff === 1) return "Yesterday";
    if (diff < 7) return `${diff} days ago`;
    return d.toLocaleDateString();
  } catch {
    return "";
  }
}

export default function SessionSidebar({
  sessions,
  currentSessionId,
  isOpen,
  onClose,
  onSelectSession,
  onDeleteSession,
  onNewChat,
}: Props) {
  if (!isOpen) return null;

  return (
    <>
      {/* Overlay for mobile */}
      <div
        className="fixed inset-0 bg-black/40 z-20 md:hidden"
        onClick={onClose}
      />

      {/* Sidebar panel */}
      <aside className="fixed md:relative z-30 md:z-auto top-0 left-0 h-full w-72 bg-nurix-navy border-r border-nurix-navyLight flex flex-col shadow-xl md:shadow-none">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-nurix-navyLight">
          <span className="font-semibold text-white text-sm tracking-wide">Chat History</span>
          <button onClick={onClose} className="p-1 rounded hover:bg-nurix-navyLight text-nurix-gold">
            <X size={16} />
          </button>
        </div>

        {/* New chat button */}
        <div className="px-3 py-2">
          <button
            onClick={onNewChat}
            className="w-full flex items-center gap-2 text-sm text-nurix-navy bg-nurix-gold hover:bg-nurix-goldHover font-semibold px-3 py-2 rounded-lg transition-colors"
          >
            <PlusCircle size={15} />
            New Chat
          </button>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto px-3 py-1">
          {sessions.length === 0 ? (
            <p className="text-xs text-nurix-gold/50 text-center py-8">No previous chats</p>
          ) : (
            <ul className="space-y-1">
              {sessions.map((session) => (
                <li key={session.id}>
                  <div
                    className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                      session.id === currentSessionId
                        ? "bg-nurix-navyLight border border-nurix-gold/40"
                        : "hover:bg-nurix-navyLight"
                    }`}
                    onClick={() => onSelectSession(session.id)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm truncate font-medium ${
                        session.id === currentSessionId ? "text-nurix-gold" : "text-gray-200"
                      }`}>
                        {session.title || "Untitled Chat"}
                      </p>
                      <p className="text-xs text-gray-400">{formatDate(session.last_active)}</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-nurix-red/20 text-gray-400 hover:text-nurix-red transition-all flex-shrink-0"
                      title="Delete chat"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </>
  );
}
