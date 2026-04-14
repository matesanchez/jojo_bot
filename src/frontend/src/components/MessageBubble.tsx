"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import { Message } from "@/lib/types";
import CitationCard from "./CitationCard";

interface Props {
  message: Message;
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h ago`;
    const diffD = Math.floor(diffH / 24);
    if (diffD === 1) return "Yesterday";
    return date.toLocaleDateString();
  } catch {
    return "";
  }
}

export default function MessageBubble({ message }: Props) {
  const [copied, setCopied] = useState(false);
  const [citationsOpen, setCitationsOpen] = useState(false);

  const isUser = message.role === "user";

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-2">
        <div className="max-w-[75%]">
          <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
          </div>
          <p className="text-right text-xs text-gray-400 mt-1 pr-1">
            {formatTimestamp(message.timestamp)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 px-4 py-2 group">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0 mt-1">
        J
      </div>

      <div className="flex-1 max-w-[80%]">
        <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-100 relative">
          {/* Copy button */}
          <button
            onClick={handleCopy}
            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100"
            title="Copy"
          >
            {copied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
          </button>

          {/* Markdown content */}
          <div className="prose prose-sm max-w-none text-gray-800">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setCitationsOpen(!citationsOpen)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
            >
              {citationsOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {message.citations.length} source{message.citations.length !== 1 ? "s" : ""}
            </button>
            {citationsOpen && (
              <div className="mt-2 space-y-1">
                {message.citations.map((c, i) => (
                  <CitationCard key={i} citation={c} index={i + 1} />
                ))}
              </div>
            )}
          </div>
        )}

        <p className="text-xs text-gray-400 mt-1 pl-1">{formatTimestamp(message.timestamp)}</p>
      </div>
    </div>
  );
}
