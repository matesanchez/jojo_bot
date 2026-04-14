"use client";

import { useRef, useState } from "react";
import { Send } from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  isLoading: boolean;
  followUpSuggestions: string[];
}

export default function InputArea({ onSend, isLoading, followUpSuggestions }: Props) {
  const [input, setInput] = useState("");
  const sendTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    onSend(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestion = (suggestion: string) => {
    if (isLoading) return;
    onSend(suggestion);
  };

  return (
    <div className="border-t border-gray-200 bg-white px-4 pt-3 pb-4">
      {/* Follow-up suggestion chips */}
      {followUpSuggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {followUpSuggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => handleSuggestion(s)}
              disabled={isLoading}
              className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full px-3 py-1 hover:bg-emerald-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input row */}
      <div className="flex items-end gap-2">
        <textarea
          className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent min-h-[48px] max-h-32 disabled:opacity-50"
          placeholder="Ask Jojo about ÄKTA operation, troubleshooting, methods..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          rows={1}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="w-11 h-11 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-200 text-white flex items-center justify-center transition-colors flex-shrink-0"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
