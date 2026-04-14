"use client";

import { FlaskConical, PlusCircle, Menu } from "lucide-react";

const INSTRUMENTS = [
  { value: "", label: "All Systems" },
  { value: "pure", label: "ÄKTA pure" },
  { value: "go", label: "ÄKTA go" },
  { value: "avant", label: "ÄKTA avant" },
  { value: "start", label: "ÄKTA start" },
  { value: "pilot_600", label: "ÄKTA pilot 600" },
  { value: "basic", label: "ÄKTA basic" },
  { value: "prime", label: "ÄKTA prime" },
  { value: "process", label: "ÄKTA process" },
  { value: "fplc", label: "ÄKTA FPLC" },
  { value: "explorer", label: "ÄKTA explorer" },
];

interface Props {
  instrumentFilter: string;
  onInstrumentChange: (value: string) => void;
  onNewChat: () => void;
  onToggleSidebar: () => void;
}

export default function Header({
  instrumentFilter,
  onInstrumentChange,
  onNewChat,
  onToggleSidebar,
}: Props) {
  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3">
      {/* Sidebar toggle */}
      <button
        onClick={onToggleSidebar}
        className="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-600"
        title="Toggle history"
      >
        <Menu size={20} />
      </button>

      {/* Logo */}
      <div className="flex items-center gap-2 min-w-max">
        <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center">
          <FlaskConical size={16} className="text-white" />
        </div>
        <div>
          <span className="font-bold text-gray-900 text-sm">Jojo Bot</span>
          <p className="text-xs text-gray-500 leading-none">ÄKTA Purification Expert</p>
        </div>
      </div>

      {/* Instrument filter */}
      <div className="flex-1 flex justify-center">
        <select
          value={instrumentFilter}
          onChange={(e) => onInstrumentChange(e.target.value)}
          className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white text-gray-700 max-w-[200px]"
        >
          {INSTRUMENTS.map((inst) => (
            <option key={inst.value} value={inst.value}>
              {inst.label}
            </option>
          ))}
        </select>
      </div>

      {/* New chat */}
      <button
        onClick={onNewChat}
        className="flex items-center gap-1.5 text-sm bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg transition-colors"
      >
        <PlusCircle size={15} />
        <span className="hidden sm:inline">New Chat</span>
      </button>
    </header>
  );
}
