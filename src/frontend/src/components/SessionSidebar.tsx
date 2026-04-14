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
        className="fixed inset-0 bg-black/30 z-20 md:hidden"
        onClick={onClose}
      />

      {/* Sidebar panel */}
      <aside className="fixed md:relative z-30 md:z-auto top-0 left-0 h-full w-72 bg-white border-r border-gray-200 flex flex-col shadow-lg md:shadow-none">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <span className="font-semibold text-gray-800 text-sm">Chat History</span>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-500">
            <X size={16} />
          </button>
        </div>

        {/* New chat button */}
        <div className="px-3 py-2">
          <button
            onClick={onNewChat}
            className="w-full flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3 py-2 rounded-lg transition-colors"
          >
            <PlusCircle size={15} />
            New Chat
          </button>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto px-3 py-1">
          {sessions.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-8">No previous chats</p>
          ) : (
            <ul className="space-y-1">
              {sessions.map((session) => (
                <li key={session.id}>
                  <div
                    className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                      session.id === currentSessionId
                        ? "bg-emerald-50 border border-emerald-200"
                        : "hover:bg-gray-100"
                    }`}
                    onClick={() => onSelectSession(session.id)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-800 truncate font-medium">
                        {session.title || "Untitled Chat"}
                      </p>
                      <p className="text-xs text-gray-400">{formatDate(session.last_active)}</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 text-gray-400 hover:text-red-500 transition-all flex-shrink-0"
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
