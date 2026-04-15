"use client";

import { useState } from "react";
import { Citation } from "@/lib/types";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";

interface Props {
  citation: Citation;
  index: number;
}

const SAFETY_KEYWORDS = ["warning", "caution", "danger", "safety", "hazard", "naoh", "pressure"];

function isSafety(citation: Citation): boolean {
  const text = `${citation.document} ${citation.section} ${citation.excerpt}`.toLowerCase();
  return SAFETY_KEYWORDS.some((kw) => text.includes(kw));
}

export default function CitationCard({ citation, index }: Props) {
  const [expanded, setExpanded] = useState(false);
  const safety = isSafety(citation);

  return (
    <div
      className={`rounded-lg border text-sm overflow-hidden transition-all ${
        safety ? "border-amber-300 bg-amber-50" : "border-blue-100 bg-blue-50"
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/40 transition-colors"
      >
        <FileText
          size={14}
          className={safety ? "text-amber-600 flex-shrink-0" : "text-blue-600 flex-shrink-0"}
        />
        <span className="flex-1 font-medium text-gray-800 truncate">
          [{index}] {citation.document}
        </span>
        {citation.section && (
          <span className="text-gray-500 text-xs truncate max-w-[120px]">{citation.section}</span>
        )}
        {citation.page && (
          <span className="text-gray-400 text-xs flex-shrink-0">p. {citation.page}</span>
        )}
        {expanded ? (
          <ChevronUp size={14} className="flex-shrink-0 text-gray-400" />
        ) : (
          <ChevronDown size={14} className="flex-shrink-0 text-gray-400" />
        )}
      </button>

      {expanded && citation.excerpt && (
        <div className="px-3 pb-3 pt-1">
          <p className="text-gray-600 italic text-xs leading-relaxed border-t border-gray-200 pt-2">
            &ldquo;{citation.excerpt}&rdquo;
          </p>
        </div>
      )}
    </div>
  );
}
