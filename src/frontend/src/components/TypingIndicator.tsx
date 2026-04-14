"use client";

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      {/* Jojo avatar */}
      <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
        J
      </div>
      {/* Bouncing dots */}
      <div className="flex items-center gap-1 bg-white rounded-2xl px-4 py-3 shadow-sm border border-gray-100">
        <span
          className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce"
          style={{ animationDelay: "0ms" }}
        />
        <span
          className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce"
          style={{ animationDelay: "150ms" }}
        />
        <span
          className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce"
          style={{ animationDelay: "300ms" }}
        />
      </div>
    </div>
  );
}
