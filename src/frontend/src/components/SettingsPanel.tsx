"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Check,
  ChevronDown,
  Eye,
  EyeOff,
  FileText,
  Loader2,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import {
  deleteApiKey,
  deleteKbDocument,
  getApiKeyStatus,
  getKnowledgeBase,
  saveApiKey,
  uploadDocuments,
} from "@/lib/api";
import { ApiKeyStatus, KbDocument } from "@/lib/types";

// Instrument options for the upload tag picker
const INSTRUMENT_OPTIONS = [
  { value: "general", label: "General / Other" },
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
  { value: "purifier", label: "ÄKTA purifier" },
  { value: "unicorn", label: "UNICORN software" },
];

type Tab = "apikey" | "kb";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onApiKeyChange: (configured: boolean) => void;
}

// ---------------------------------------------------------------------------
// API Key Tab
// ---------------------------------------------------------------------------
function ApiKeyTab({ onApiKeyChange }: { onApiKeyChange: (v: boolean) => void }) {
  const [status, setStatus] = useState<ApiKeyStatus | null>(null);
  const [inputKey, setInputKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<"success" | "error" | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    getApiKeyStatus()
      .then(setStatus)
      .catch(() => setStatus({ configured: false, masked_key: null }));
  }, []);

  const handleSave = async () => {
    if (!inputKey.trim()) return;
    setSaving(true);
    setSaveResult(null);
    setErrorMsg("");
    try {
      await saveApiKey(inputKey.trim());
      const fresh = await getApiKeyStatus();
      setStatus(fresh);
      setInputKey("");
      setSaveResult("success");
      onApiKeyChange(true);
      setTimeout(() => setSaveResult(null), 3000);
    } catch (e: unknown) {
      setSaveResult("error");
      setErrorMsg(e instanceof Error ? e.message : "Could not save key.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Remove the stored API key? Jojo Bot won't be able to answer questions until a new key is added.")) return;
    try {
      await deleteApiKey();
      setStatus({ configured: false, masked_key: null });
      onApiKeyChange(false);
    } catch {
      alert("Could not remove the key.");
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-sm font-semibold text-gray-800 mb-1">Anthropic API Key</h3>
        <p className="text-xs text-gray-500">
          Your key is stored only on <strong>this computer</strong> (in your user profile) and is
          never included in any shared package.
        </p>
      </div>

      {/* Current key status */}
      {status?.configured ? (
        <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3">
          <div className="flex items-center gap-2">
            <Check size={14} className="text-emerald-600 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-emerald-800">Key configured</p>
              <p className="text-xs text-emerald-600 font-mono">{status.masked_key}</p>
            </div>
          </div>
          <button
            onClick={handleDelete}
            className="p-1.5 rounded hover:bg-red-100 text-gray-400 hover:text-red-500 transition-colors"
            title="Remove key"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ) : (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
          <p className="text-xs text-amber-700">
            ⚠️ No API key set. Jojo Bot needs an Anthropic API key to answer questions.
            Get one at{" "}
            <a
              href="https://console.anthropic.com"
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              console.anthropic.com
            </a>
            .
          </p>
        </div>
      )}

      {/* Input for new / replacement key */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1.5">
          {status?.configured ? "Replace key" : "Enter your API key"}
        </label>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type={showKey ? "text" : "password"}
              value={inputKey}
              onChange={(e) => setInputKey(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              placeholder="sk-ant-api03-..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 pr-10 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-nurix-gold"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          <button
            onClick={handleSave}
            disabled={saving || !inputKey.trim()}
            className="flex items-center gap-1.5 bg-nurix-navy hover:bg-nurix-navyDark disabled:bg-gray-200 disabled:text-gray-400 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            {saving ? <Loader2 size={13} className="animate-spin" /> : null}
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
        {saveResult === "success" && (
          <p className="text-xs text-emerald-600 mt-1.5 flex items-center gap-1">
            <Check size={12} /> Key saved successfully.
          </p>
        )}
        {saveResult === "error" && (
          <p className="text-xs text-red-500 mt-1.5">{errorMsg || "Could not save key."}</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Knowledge Base Tab
// ---------------------------------------------------------------------------
function KnowledgeBaseTab() {
  const [docs, setDocs] = useState<KbDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [instrument, setInstrument] = useState("general");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    current: number;
    total: number;
    filename: string;
  } | null>(null);
  const [uploadResult, setUploadResult] = useState<{
    chunks: number;
    errors: string[];
  } | null>(null);
  const [uploadError, setUploadError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocs = useCallback(() => {
    setLoading(true);
    setLoadError("");
    getKnowledgeBase()
      .then((res) => setDocs(res.documents))
      .catch((e: unknown) => {
        // Distinguish "backend unreachable" from a valid empty KB so the
        // user isn't silently shown "No documents found" when the real
        // problem is that the backend process never started.
        setDocs([]);
        const msg = e instanceof Error ? e.message : String(e);
        setLoadError(
          msg.includes("Failed to fetch") || msg.includes("NetworkError")
            ? "Could not reach the backend. Make sure the Jojo Bot backend window is running, then click Retry."
            : `Couldn't load the knowledge base: ${msg}`
        );
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files).filter((f) =>
      f.name.toLowerCase().endsWith(".pdf")
    );
    if (dropped.length) setSelectedFiles(dropped);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files || []);
    if (picked.length) setSelectedFiles(picked);
  };

  const handleUpload = async () => {
    if (!selectedFiles.length) return;
    setUploading(true);
    setUploadProgress(null);
    setUploadResult(null);
    setUploadError("");

    try {
      for await (const event of uploadDocuments(selectedFiles, instrument)) {
        if (event.type === "progress") {
          setUploadProgress({
            current: event.current,
            total: event.total,
            filename: event.filename,
          });
        } else if (event.type === "done") {
          setUploadResult({ chunks: event.chunks_added, errors: event.errors });
          setSelectedFiles([]);
          if (fileInputRef.current) fileInputRef.current.value = "";
          loadDocs();
        } else if (event.type === "error") {
          setUploadError(event.message);
        }
      }
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
      setUploadProgress(null);
    }
  };

  const handleDelete = async (sourceFile: string) => {
    if (!confirm(`Remove "${sourceFile}" from Jojo Bot's knowledge base?`)) return;
    try {
      await deleteKbDocument(sourceFile);
      setDocs((prev) => prev.filter((d) => d.source_file !== sourceFile));
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Could not delete document.");
    }
  };

  const baseDocs = docs.filter((d) => d.category === "base");
  const userDocs = docs.filter((d) => d.category === "user");

  return (
    <div className="space-y-5">
      {/* Document list */}
      <div>
        <h3 className="text-sm font-semibold text-gray-800 mb-3">
          Installed Documents
          <span className="ml-2 text-xs font-normal text-gray-400">
            {loading ? "Loading…" : `${docs.length} total`}
          </span>
        </h3>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={20} className="animate-spin text-nurix-gold" />
          </div>
        ) : loadError ? (
          <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-700 flex items-start justify-between gap-2">
            <span>{loadError}</span>
            <button
              onClick={loadDocs}
              className="px-2 py-0.5 border border-red-300 rounded text-red-700 hover:bg-red-100 flex-shrink-0"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="space-y-3 max-h-52 overflow-y-auto pr-1">
            {/* User-uploaded docs */}
            {userDocs.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-nurix-navy uppercase tracking-wide mb-1.5">
                  Your Documents ({userDocs.length})
                </p>
                <ul className="space-y-1">
                  {userDocs.map((doc) => (
                    <li
                      key={doc.source_file}
                      className="flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2"
                    >
                      <FileText size={13} className="text-blue-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-800 truncate">{doc.doc_title}</p>
                        <p className="text-xs text-gray-400 truncate">{doc.source_file}</p>
                      </div>
                      <button
                        onClick={() => handleDelete(doc.source_file)}
                        className="p-1 rounded hover:bg-red-100 text-gray-300 hover:text-red-500 transition-colors flex-shrink-0"
                        title="Remove"
                      >
                        <Trash2 size={12} />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Base docs (collapsed by default) */}
            {baseDocs.length > 0 && (
              <details className="group">
                <summary className="cursor-pointer text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1 select-none">
                  <ChevronDown
                    size={12}
                    className="transition-transform group-open:rotate-0 -rotate-90"
                  />
                  Base Knowledge ({baseDocs.length} documents)
                </summary>
                <ul className="space-y-1 mt-1">
                  {baseDocs.map((doc) => (
                    <li
                      key={doc.source_file}
                      className="flex items-center gap-2 bg-gray-50 border border-gray-100 rounded-lg px-3 py-2"
                    >
                      <FileText size={13} className="text-gray-300 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-700 truncate">{doc.doc_title}</p>
                        <p className="text-xs text-gray-400 truncate">
                          {doc.instruments.join(", ")} · {doc.chunk_count} chunks
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              </details>
            )}

            {docs.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-4">
                No documents found. Run the ingest script to populate the knowledge base.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-gray-100" />

      {/* Upload area */}
      <div>
        <h3 className="text-sm font-semibold text-gray-800 mb-3">Add Documents</h3>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleFileDrop}
          onClick={() => !uploading && fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl px-4 py-6 text-center cursor-pointer transition-colors ${
            dragOver
              ? "border-nurix-gold bg-amber-50"
              : selectedFiles.length
              ? "border-nurix-navy bg-blue-50"
              : "border-gray-200 hover:border-gray-300 bg-white"
          } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <Upload
            size={20}
            className={`mx-auto mb-2 ${selectedFiles.length ? "text-nurix-navy" : "text-gray-300"}`}
          />
          {selectedFiles.length > 0 ? (
            <p className="text-sm font-medium text-nurix-navy">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? "s" : ""} selected
            </p>
          ) : (
            <>
              <p className="text-sm text-gray-500">Drop PDFs here or click to browse</p>
              <p className="text-xs text-gray-400 mt-0.5">Accepts .pdf files only</p>
            </>
          )}
          {selectedFiles.length > 0 && (
            <ul className="mt-2 text-xs text-gray-500 space-y-0.5">
              {selectedFiles.map((f) => (
                <li key={f.name} className="truncate max-w-xs mx-auto">{f.name}</li>
              ))}
            </ul>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf"
          className="hidden"
          onChange={handleFileInput}
        />

        {/* Instrument tag picker */}
        {selectedFiles.length > 0 && (
          <div className="mt-3">
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Document type <span className="text-gray-400 font-normal">(helps Jojo filter results)</span>
            </label>
            <select
              value={instrument}
              onChange={(e) => setInstrument(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-nurix-gold"
            >
              {INSTRUMENT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        )}

        {/* Progress bar */}
        {uploading && uploadProgress && (
          <div className="mt-3 space-y-1.5">
            <div className="flex justify-between text-xs text-gray-500">
              <span className="truncate max-w-[70%]">Processing {uploadProgress.filename}</span>
              <span>{uploadProgress.current}/{uploadProgress.total}</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="bg-nurix-gold h-2 rounded-full transition-all duration-300"
                style={{
                  width: `${Math.round((uploadProgress.current / uploadProgress.total) * 100)}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Result / error */}
        {uploadResult && (
          <div className="mt-3 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2.5">
            <p className="text-xs font-medium text-emerald-800 flex items-center gap-1">
              <Check size={12} />
              Added {uploadResult.chunks.toLocaleString()} chunks to the knowledge base.
            </p>
            {uploadResult.errors.length > 0 && (
              <ul className="mt-1 text-xs text-amber-600 space-y-0.5">
                {uploadResult.errors.map((e, i) => (
                  <li key={i} className="truncate">⚠ {e}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {uploadError && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
            <p className="text-xs text-red-600">{uploadError}</p>
          </div>
        )}

        {/* Upload button */}
        {selectedFiles.length > 0 && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-3 w-full flex items-center justify-center gap-2 bg-nurix-navy hover:bg-nurix-navyDark disabled:bg-gray-200 disabled:text-gray-400 text-white text-sm font-semibold py-2.5 rounded-lg transition-colors"
          >
            {uploading ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Ingesting…
              </>
            ) : (
              <>
                <Upload size={14} />
                Add to Knowledge Base
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main SettingsPanel
// ---------------------------------------------------------------------------
export default function SettingsPanel({ isOpen, onClose, onApiKeyChange }: Props) {
  const [tab, setTab] = useState<Tab>("apikey");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="font-bold text-gray-900">⚙️ Settings</h2>
            <p className="text-xs text-gray-400">Stored locally — never shared with others</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100 text-gray-500"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 px-6">
          {(["apikey", "kb"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                tab === t
                  ? "border-nurix-gold text-nurix-navy"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "apikey" ? "🔑 API Key" : "📚 Knowledge Base"}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {tab === "apikey" ? (
            <ApiKeyTab onApiKeyChange={onApiKeyChange} />
          ) : (
            <KnowledgeBaseTab />
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100">
          <button
            onClick={onClose}
            className="w-full text-sm text-gray-500 hover:text-gray-700 py-1 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
