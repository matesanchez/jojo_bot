"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import { X, Copy, Download, Loader2, AlertTriangle } from "lucide-react";
import { generateProtocol } from "@/lib/api";
import { ProtocolResponse } from "@/lib/types";

const PURIFICATION_TYPES = [
  { value: "affinity", label: "Affinity (His-tag)" },
  { value: "affinity_gst", label: "Affinity (GST-tag)" },
  { value: "ion_exchange", label: "Ion Exchange" },
  { value: "size_exclusion", label: "Size Exclusion" },
  { value: "hydrophobic", label: "Hydrophobic Interaction" },
  { value: "mixed", label: "Mixed / Multi-step" },
];

const INSTRUMENTS = [
  { value: "pure", label: "ÄKTA pure" },
  { value: "go", label: "ÄKTA go" },
  { value: "avant", label: "ÄKTA avant" },
  { value: "start", label: "ÄKTA start" },
];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string | null;
}

export default function ProtocolDialog({ isOpen, onClose, sessionId }: Props) {
  const [targetProtein, setTargetProtein] = useState("");
  const [purificationType, setPurificationType] = useState("affinity");
  const [instrument, setInstrument] = useState("pure");
  const [column, setColumn] = useState("");
  const [sampleVolume, setSampleVolume] = useState("");
  const [notes, setNotes] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<ProtocolResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Reset state every time the dialog opens so stale data doesn't show
  useEffect(() => {
    if (isOpen) {
      setResult(null);
      setError(null);
      setCopied(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    if (!targetProtein.trim()) return;
    setIsGenerating(true);
    setError(null);
    setResult(null);
    try {
      const res = await generateProtocol({
        target_protein: targetProtein,
        purification_type: purificationType,
        instrument,
        column: column || undefined,
        sample_volume: sampleVolume || undefined,
        additional_notes: notes || undefined,
        session_id: sessionId || undefined,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate protocol.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = () => {
    if (result) {
      navigator.clipboard.writeText(result.protocol_markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    try {
      const blob = new Blob([result.protocol_markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      // Sanitise filename — only keep alphanumerics, spaces, hyphens, underscores
      const safeName = result.protocol_title.replace(/[^\w\s\-]/g, "").replace(/\s+/g, "_");
      a.download = `${safeName || "protocol"}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Download failed:", e);
      setError("Could not download file. Try copying instead.");
    }
  };

  const handleClose = () => {
    setResult(null);
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="font-bold text-gray-900">🧪 Generate Purification Protocol</h2>
            <p className="text-xs text-gray-500">Jojo will write a step-by-step protocol based on ÄKTA manuals</p>
          </div>
          <button onClick={handleClose} className="p-1 rounded hover:bg-gray-100 text-gray-500">
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {!result ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Target Protein <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={targetProtein}
                  onChange={(e) => setTargetProtein(e.target.value)}
                  placeholder="e.g., His-tagged GFP, GST-fusion protein..."
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Purification Type</label>
                  <select
                    value={purificationType}
                    onChange={(e) => setPurificationType(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    {PURIFICATION_TYPES.map((pt) => (
                      <option key={pt.value} value={pt.value}>{pt.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Instrument</label>
                  <select
                    value={instrument}
                    onChange={(e) => setInstrument(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    {INSTRUMENTS.map((inst) => (
                      <option key={inst.value} value={inst.value}>{inst.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Column (optional)</label>
                  <input
                    type="text"
                    value={column}
                    onChange={(e) => setColumn(e.target.value)}
                    placeholder="e.g., HisTrap HP 5 mL"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Sample Volume (optional)</label>
                  <input
                    type="text"
                    value={sampleVolume}
                    onChange={(e) => setSampleVolume(e.target.value)}
                    placeholder="e.g., 50 mL"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Additional Notes (optional)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Any specific requirements, pH targets, salt concentrations..."
                  rows={3}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
                />
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}
            </div>
          ) : (
            /* Protocol result */
            <div>
              {result.warnings.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle size={14} className="text-amber-600" />
                    <span className="text-sm font-medium text-amber-800">Safety Reminders</span>
                  </div>
                  <ul className="text-xs text-amber-700 space-y-1">
                    {result.warnings.map((w, i) => (
                      <li key={i}>• {w}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{result.protocol_markdown}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          {result ? (
            <>
              <button
                onClick={handleCopy}
                className="flex items-center gap-2 text-sm border border-gray-300 rounded-lg px-4 py-2 hover:bg-gray-50 transition-colors"
              >
                <Copy size={14} />
                {copied ? "Copied!" : "Copy"}
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 text-sm bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg px-4 py-2 transition-colors"
              >
                <Download size={14} />
                Download .md
              </button>
              <button
                onClick={() => { setResult(null); setError(null); }}
                disabled={isGenerating}
                className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed px-2"
              >
                Regenerate
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleClose}
                className="text-sm border border-gray-300 rounded-lg px-4 py-2 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={isGenerating || !targetProtein.trim()}
                className="flex items-center gap-2 text-sm bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-200 text-white rounded-lg px-4 py-2 transition-colors"
              >
                {isGenerating ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Jojo is writing your protocol...
                  </>
                ) : (
                  "Generate Protocol"
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
