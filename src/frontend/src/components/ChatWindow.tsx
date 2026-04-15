"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import { Settings } from "lucide-react";
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
  apiKeyConfigured: boolean;
  onQuickAction: (message: string) => void;
  onOpenSettings: () => void;
}

export default function ChatWindow({
  messages,
  isLoading,
  apiKeyConfigured,
  onQuickAction,
  onOpenSettings,
}: Props) {
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
          <div className="w-20 h-20 rounded-full overflow-hidden ring-4 ring-nurix-gold ring-offset-2 ring-offset-gray-50 mb-5 shadow-lg">
            <Image
              src="/jojo-avatar.png"
              alt="Jojo Bot"
              width={80}
              height={80}
              className="w-full h-full object-cover"
            />
          </div>
          <h2 className="text-2xl font-bold text-nurix-navy mb-2">Welcome to Jojo Bot</h2>
          <p className="text-gray-500 mb-1 max-w-md">
            Your AI expert for Cytiva ÄKTA chromatography systems and Nurix purification SOPs.
          </p>
          <p className="text-gray-400 text-sm mb-6 max-w-md">
            Ask anything about operating, troubleshooting, or maintaining ÄKTA systems —
            grounded in official Cytiva manuals and your lab&apos;s own SOPs.
          </p>

          {/* API key prompt banner */}
          {!apiKeyConfigured && (
            <button
              onClick={onOpenSettings}
              className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-xl px-5 py-3 mb-6 text-amber-700 hover:bg-amber-100 transition-colors"
            >
              <Settings size={16} className="flex-shrink-0" />
              <span className="text-sm font-medium">
                Add your Anthropic API key in Settings to start chatting
              </span>
            </button>
          )}

          {/* Quick action grid */}
          <div className="grid grid-cols-2 gap-3 w-full max-w-md">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                onClick={() => onQuickAction(action.message)}
                className="flex items-center gap-2 bg-white border border-gray-200 hover:border-nurix-gold hover:bg-amber-50 rounded-xl px-4 py-3 text-left transition-colors shadow-sm"
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
