"use client";

import { Menu, PlusCircle, Settings } from "lucide-react";
import Image from "next/image";

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
  onOpenSettings: () => void;
  apiKeyConfigured: boolean;
}

export default function Header({
  instrumentFilter,
  onInstrumentChange,
  onNewChat,
  onToggleSidebar,
  onOpenSettings,
  apiKeyConfigured,
}: Props) {
  return (
    <header className="bg-nurix-navy border-b border-nurix-navyLight px-4 py-3 flex items-center gap-3 shadow-md">
      {/* Sidebar toggle */}
      <button
        onClick={onToggleSidebar}
        className="p-2 rounded-lg hover:bg-nurix-navyLight transition-colors text-nurix-gold"
        title="Toggle history"
      >
        <Menu size={20} />
      </button>

      {/* Logo + avatar */}
      <div className="flex items-center gap-2.5 min-w-max">
        <div className="w-9 h-9 rounded-full overflow-hidden ring-2 ring-nurix-gold ring-offset-1 ring-offset-nurix-navy flex-shrink-0">
          <Image
            src="/jojo-avatar.png"
            alt="Jojo Bot"
            width={36}
            height={36}
            className="w-full h-full object-cover"
          />
        </div>
        <div>
          <span className="font-bold text-white text-sm tracking-wide">Jojo Bot</span>
          <p className="text-xs text-nurix-gold leading-none opacity-90">Purification Expert</p>
        </div>
      </div>

      {/* Instrument filter */}
      <div className="flex-1 flex justify-center">
        <select
          value={instrumentFilter}
          onChange={(e) => onInstrumentChange(e.target.value)}
          className="text-sm border border-nurix-navyLight rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-nurix-gold bg-nurix-navyLight text-white max-w-[200px]"
        >
          {INSTRUMENTS.map((inst) => (
            <option key={inst.value} value={inst.value}>
              {inst.label}
            </option>
          ))}
        </select>
      </div>

      {/* Right side buttons */}
      <div className="flex items-center gap-1.5">
        {/* Settings gear — red dot badge when no API key configured */}
        <button
          onClick={onOpenSettings}
          className="relative p-2 rounded-lg hover:bg-nurix-navyLight transition-colors text-nurix-gold"
          title="Settings"
        >
          <Settings size={18} />
          {!apiKeyConfigured && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-nurix-red rounded-full border border-nurix-navy" />
          )}
        </button>

        {/* New chat */}
        <button
          onClick={onNewChat}
          className="flex items-center gap-1.5 text-sm bg-nurix-gold hover:bg-nurix-goldHover text-nurix-navy font-semibold px-3 py-1.5 rounded-lg transition-colors"
        >
          <PlusCircle size={15} />
          <span className="hidden sm:inline">New Chat</span>
        </button>
      </div>
    </header>
  );
}
