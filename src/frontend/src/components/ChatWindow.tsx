"use client";

import { useEffect, useRef } from "react";
import { Message } from "@/lib/types";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

const QUICK_ACTIONS = [
  {
    icon: "🔧",
    label: "Troubleshoot My System",
    message: "My ÄKTA pure is showing high backpressure. How do I troubleshoot this?",
  },
  {
    icon: "📋",
    label: "Create a UNICORN Method",
    message: "How do I create a gradient method in UNICORN 7?",
  },
  {
    icon: "🧹",
    label: "Maintenance Schedule",
    message: "What is the recommended maintenance schedule for the ÄKTA pure?",
  },
  {
    icon: "🧪",
    label: "Generate a Protocol",
    message: "Generate a protocol for",
  },
];

interface Props {
  messages: Message[];
  isLoading: boolean;
  onQuickAction: (message: string) => void;
}

export default function ChatWindow({ messages, isLoading, onQuickAction }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex-1 overflow-y-auto chat-scroll">
      {isEmpty ? (
        /* Welcome screen */
        <div className="flex flex-col items-center justify-center h-full px-6 text-center">
          <div className="w-16 h-16 rounded-full bg-emerald-600 flex items-center justify-center mb-4">
            <span className="text-white text-2xl font-bold">J</span>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Welcome to Jojo Bot</h2>
          <p className="text-gray-500 mb-2 max-w-md">
            Your AI expert for Cytiva ÄKTA chromatography systems and UNICORN software.
          </p>
          <p className="text-gray-400 text-sm mb-8 max-w-md">
            Ask me anything about operating, troubleshooting, or maintaining ÄKTA systems —
            grounded in 43 official Cytiva manuals.
          </p>

          {/* Quick action grid */}
          <div className="grid grid-cols-2 gap-3 w-full max-w-md">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                onClick={() => onQuickAction(action.message)}
                className="flex items-center gap-2 bg-white border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50 rounded-xl px-4 py-3 text-left transition-colors shadow-sm"
              >
                <span className="text-xl">{action.icon}</span>
                <span className="text-sm font-medium text-gray-700">{action.label}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        /* Message list */
        <div className="py-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          {isLoading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
