"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Lock, Unlock, Eye, EyeOff,
  Play, CheckCircle, XCircle, Loader2,
  ChevronDown, ChevronUp, Save,
} from "lucide-react";
import { clsx } from "clsx";
import { triggerIngest } from "@/lib/api";
import type { IngestStatus } from "@/lib/api";

// ─── Modèles par provider (Groq mis à jour avril 2025) ────────────
const PROVIDER_MODELS: Record<string, string[]> = {
  groq: [
    "llama-3.3-70b-versatile",
    "compound-beta",
    "moonshotai/kimi-k2-instruct-0905",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "deepseek-r1-distill-llama-70b",
  ],
  openai:    ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
  anthropic: ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
  gemini:    ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
  ollama:    ["llama3.1", "mistral", "gemma3:12b", "deepseek-r1:8b"],
};

const PROVIDERS = Object.keys(PROVIDER_MODELS) as (keyof typeof PROVIDER_MODELS)[];

const LS = {
  provider:    "oracle_provider",
  model:       "oracle_model",
  temperature: "oracle_temperature",
  k_final:     "oracle_k_final",
  apiKeys:     "oracle_api_keys",
};

// ─── Section wrapper ──────────────────────────────────────────────
function Section({ title, children, defaultOpen = true }: {
  title: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-default rounded-xl overflow-hidden bg-surface animate-fade-up">
      <button onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-subtle transition-colors duration-150 text-left">
        <span className="text-sm font-medium text-main">{title}</span>
        {open ? <ChevronUp size={14} className="text-muted-fg" /> : <ChevronDown size={14} className="text-muted-fg" />}
      </button>
      {open && <div className="px-5 pb-5 border-t border-default space-y-4 pt-4">{children}</div>}
    </div>
  );
}

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-fg uppercase tracking-wide">{label}</label>
      {children}
      {hint && <p className="text-xs text-subtle-fg">{hint}</p>}
    </div>
  );
}

const inputClass = `w-full px-3 py-2 rounded-lg border border-default bg-surface-alt text-sm text-main
  placeholder:text-subtle-fg focus:outline-none focus:border-gold/50 transition-colors duration-150`;

// ─── Composant principal ──────────────────────────────────────────
export function AdminPanel() {
  const [unlocked,     setUnlocked]     = useState(false);
  const [password,     setPassword]     = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [authError,    setAuthError]    = useState(false);

  // Config IA — chargée depuis localStorage
  const [provider,    setProvider]    = useState("groq");
  const [model,       setModel]       = useState("llama-3.3-70b-versatile");
  const [temperature, setTemperature] = useState(0);
  const [kFinal,      setKFinal]      = useState(5);
  const [saveStatus,  setSaveStatus]  = useState<"idle" | "saved">("idle");

  // Clés API
  const [apiKeys,     setApiKeys]     = useState<Record<string, string>>({
    groq: "", openai: "", anthropic: "", gemini: "",
  });
  const [keySaveStatus, setKeySaveStatus] = useState<"idle" | "saved">("idle");

  // Test provider
  const [testMsg,    setTestMsg]    = useState("Dis-moi qui tu es en une phrase.");
  const [testState,  setTestState]  = useState<"idle" | "running" | "success" | "error">("idle");
  const [testOutput, setTestOutput] = useState("");

  // Health check
  const [healthData,  setHealthData]  = useState<any>(null);
  const [healthState, setHealthState] = useState<"idle" | "running" | "done">("idle");

  // Logs
  const [logs,        setLogs]        = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Ingestion
  const [folderPath,  setFolderPath]  = useState("");
  const [ingestState, setIngestState] = useState<IngestStatus["last_status"]>("idle");
  const [ingestMsg,   setIngestMsg]   = useState("");

  // Charger depuis localStorage au montage
  useEffect(() => {
    setProvider(localStorage.getItem(LS.provider) || "groq");
    setModel(localStorage.getItem(LS.model) || "llama-3.3-70b-versatile");
    setTemperature(parseFloat(localStorage.getItem(LS.temperature) || "0"));
    setKFinal(parseInt(localStorage.getItem(LS.k_final) || "5"));
    try {
      const saved = localStorage.getItem(LS.apiKeys);
      if (saved) setApiKeys(JSON.parse(saved));
    } catch {}
  }, []);

  const handleLogin = () => {
    const expected = process.env.NEXT_PUBLIC_ADMIN_PASSWORD ?? "oracle";
    if (password === expected) { setUnlocked(true); setAuthError(false); }
    else setAuthError(true);
  };

  const handleSaveConfig = () => {
    localStorage.setItem(LS.provider,    provider);
    localStorage.setItem(LS.model,       model);
    localStorage.setItem(LS.temperature, String(temperature));
    localStorage.setItem(LS.k_final,     String(kFinal));
    setSaveStatus("saved");
    setTimeout(() => setSaveStatus("idle"), 2000);
  };

  const handleSaveKeys = () => {
    localStorage.setItem(LS.apiKeys, JSON.stringify(apiKeys));
    setKeySaveStatus("saved");
    setTimeout(() => setKeySaveStatus("idle"), 2000);
  };

  const handleTestProvider = async () => {
    setTestState("running");
    setTestOutput("⏳ Test en cours…");
    try {
      const res = await fetch("/api/admin/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, model, message: testMsg, temperature, k_final: 1 }),
      });
      const data = await res.json();
      if (!res.ok) {
        setTestState("error");
        setTestOutput(`❌ ${data.error || data.detail || "Erreur inconnue"}`);
        return;
      }
      setTestState("success");
      setTestOutput(`✅ Provider: ${data.provider} · Modèle: ${data.model}\n\n${data.response}`);
    } catch (e: any) {
      setTestState("error");
      setTestOutput(`❌ ${e.message}`);
    }
  };

  const fetchLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const res = await fetch("/api/admin/logs?lines=150");
      const data = await res.json();
      setLogs(data.logs || []);
      setTimeout(() => logsEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch { } finally {
      setLogsLoading(false);
    }
  }, []);

  const clearLogs = async () => {
    await fetch("/api/admin/logs", { method: "DELETE" });
    setLogs([]);
  };

  // Auto-refresh logs toutes les 3s si activé
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchLogs, 3000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchLogs]);

  const handleHealthCheck = async () => {
    setHealthState("running");
    setHealthData(null);
    try {
      const res = await fetch("/api/admin/health");
      const data = await res.json();
      setHealthData(data);
    } catch (e: any) {
      setHealthData({ status: "error", checks: { backend: { status: "error", error: e.message } } });
    } finally {
      setHealthState("done");
    }
  };

  const handleTriggerIngest = async () => {
    setIngestState("running");
    setIngestMsg("Démarrage…");
    try {
      await triggerIngest(folderPath);
      const poll = setInterval(async () => {
        try {
          const res = await fetch("/api/admin/ingest/status");
          const status = await res.json();
          setIngestMsg(status.last_message || "En cours…");
          if (!status.running) {
            clearInterval(poll);
            setIngestState(status.last_status === "success" ? "success" : "error");
            setIngestMsg(status.last_status === "success" ? "Terminée avec succès ✓" : status.last_message);
          }
        } catch { clearInterval(poll); setIngestState("error"); }
      }, 2000);
    } catch (e: any) {
      setIngestState("error");
      setIngestMsg(e.message);
    }
  };

  if (!unlocked) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] animate-fade-in">
        <div className="w-full max-w-sm space-y-4">
          <div className="text-center mb-6">
            <Lock size={28} className="mx-auto text-gold mb-3" />
            <p className="text-sm text-muted-fg">Accès réservé aux administrateurs</p>
          </div>
          <div className="relative">
            <input type={showPassword ? "text" : "password"} value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleLogin()}
              placeholder="Mot de passe admin"
              className={clsx(inputClass, "pr-10", authError && "border-red-400/50")} />
            <button onClick={() => setShowPassword(v => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-subtle-fg hover:text-main">
              {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          {authError && <p className="text-xs text-red-400 text-center">Mot de passe incorrect</p>}
          <button onClick={handleLogin}
            className="w-full py-2.5 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light transition-colors duration-150">
            Accéder
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">

      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-sm text-green-400">
          <Unlock size={13} /><span>Session admin active</span>
        </div>
        <button onClick={() => setUnlocked(false)} className="text-xs text-muted-fg hover:text-main transition-colors">
          Se déconnecter
        </button>
      </div>

      {/* Modèle IA */}
      <Section title="Modèle IA">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Provider">
            <select value={provider}
              onChange={e => { setProvider(e.target.value); setModel(PROVIDER_MODELS[e.target.value]?.[0] ?? ""); }}
              className={inputClass}>
              {PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </Field>
          <Field label="Modèle">
            <select value={model} onChange={e => setModel(e.target.value)} className={inputClass}>
              {(PROVIDER_MODELS[provider] ?? []).map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
        </div>

        <Field label={`Température — ${temperature}`} hint="0 = déterministe · 1 = créatif">
          <input type="range" min={0} max={1} step={0.05} value={temperature}
            onChange={e => setTemperature(parseFloat(e.target.value))}
            className="w-full accent-gold" />
        </Field>

        <Field label={`K final (chunks RAG) — ${kFinal}`} hint="Nombre de chunks retournés par la recherche">
          <input type="range" min={1} max={15} step={1} value={kFinal}
            onChange={e => setKFinal(parseInt(e.target.value))}
            className="w-full accent-gold" />
        </Field>

        <button onClick={handleSaveConfig}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light transition-colors duration-150">
          {saveStatus === "saved"
            ? <><CheckCircle size={13} /> Sauvegardé !</>
            : <><Save size={13} /> Sauvegarder la configuration</>}
        </button>
      </Section>

      {/* Clés API */}
      <Section title="Clés API" defaultOpen={false}>
        <p className="text-xs text-muted-fg">Les clés sont stockées localement dans votre navigateur.</p>
        {Object.keys(apiKeys).map(p => (
          <Field key={p} label={p}>
            <input type="password" value={apiKeys[p]}
              onChange={e => setApiKeys(k => ({ ...k, [p]: e.target.value }))}
              placeholder={`Clé ${p}…`} className={inputClass} />
          </Field>
        ))}
        <button onClick={handleSaveKeys}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light transition-colors duration-150">
          {keySaveStatus === "saved"
            ? <><CheckCircle size={13} /> Clés sauvegardées !</>
            : <><Save size={13} /> Sauvegarder les clés</>}
        </button>
      </Section>

      {/* Test provider */}
      <Section title="Test du Provider" defaultOpen={false}>
        <Field label="Message de test">
          <textarea value={testMsg} onChange={e => setTestMsg(e.target.value)}
            className={clsx(inputClass, "resize-none h-20")} />
        </Field>
        <button onClick={handleTestProvider} disabled={testState === "running"}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150">
          {testState === "running"
            ? <><Loader2 size={13} className="animate-spin" /> Test en cours…</>
            : <>🧪 Tester le provider</>}
        </button>
        {testState !== "idle" && (
          <div className={clsx("mt-3 p-3 rounded-lg text-xs font-mono whitespace-pre-wrap break-words",
            testState === "success" && "bg-green-400/10 text-green-300 border border-green-400/30",
            testState === "error"   && "bg-red-400/10 text-red-300 border border-red-400/30",
            testState === "running" && "bg-blue-400/10 text-blue-300 border border-blue-400/30",
          )}>{testOutput}</div>
        )}
      </Section>

      {/* Logs */}
      <Section title="Logs système" defaultOpen={false}>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={fetchLogs} disabled={logsLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gold text-white text-xs font-medium hover:bg-gold-light disabled:opacity-40 transition-colors">
            {logsLoading ? <><Loader2 size={11} className="animate-spin" /> Chargement…</> : "🔄 Actualiser"}
          </button>
          <button onClick={() => setAutoRefresh(v => !v)}
            className={clsx("px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
              autoRefresh ? "bg-green-400/20 border-green-400/40 text-green-300" : "border-default text-muted-fg hover:text-main")}>
            {autoRefresh ? "⏸ Auto-refresh ON" : "▶ Auto-refresh OFF"}
          </button>
          <button onClick={clearLogs}
            className="px-3 py-1.5 rounded-lg text-xs font-medium border border-red-400/30 text-red-400 hover:bg-red-400/10 transition-colors ml-auto">
            🗑 Vider les logs
          </button>
        </div>

        <div className="bg-[#0a0c10] rounded-lg border border-default overflow-auto h-64 p-3 font-mono text-xs">
          {logs.length === 0 ? (
            <p className="text-muted-fg">Aucun log — cliquez sur Actualiser</p>
          ) : (
            logs.map((line, i) => (
              <div key={i} className={clsx("leading-5",
                line.includes("ERROR")   && "text-red-400",
                line.includes("WARNING") && "text-amber-400",
                line.includes("INFO")    && "text-green-300",
                !line.includes("ERROR") && !line.includes("WARNING") && !line.includes("INFO") && "text-muted-fg",
              )}>
                {line}
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </Section>

      {/* Health Check */}
      <Section title="Health Check" defaultOpen={false}>
        <button onClick={handleHealthCheck} disabled={healthState === "running"}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150">
          {healthState === "running"
            ? <><Loader2 size={13} className="animate-spin" /> Vérification en cours…</>
            : <>🔍 Vérifier l'état du système</>}
        </button>

        {healthData && (
          <div className="space-y-2 mt-2">
            {Object.entries(healthData.checks || {}).map(([key, val]: [string, any]) => (
              <div key={key} className={clsx(
                "flex items-center justify-between px-3 py-2 rounded-lg text-xs border",
                val.status === "ok"             && "bg-green-400/10 border-green-400/30 text-green-300",
                val.status === "error"          && "bg-red-400/10 border-red-400/30 text-red-300",
                val.status === "not_configured" && "bg-subtle border-default text-muted-fg",
              )}>
                <div className="flex items-center gap-2">
                  <span>
                    {val.status === "ok"             && "✅"}
                    {val.status === "error"          && "❌"}
                    {val.status === "not_configured" && "⚪"}
                  </span>
                  <span className="font-medium capitalize">{key}</span>
                  {val.documents !== undefined && (
                    <span className="opacity-70">{val.documents} documents</span>
                  )}
                  {val.model && <span className="opacity-70">{val.model}</span>}
                </div>
                <div className="text-right">
                  {val.latency_ms && <span className="opacity-70">{val.latency_ms}ms</span>}
                  {val.error && <span className="max-w-[200px] truncate" title={val.error}>{val.error}</span>}
                  {val.status === "not_configured" && <span>Non configuré</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Ingestion */}
      <Section title="Ingestion">
        <Field label="Chemin du dossier" hint="Chemin absolu contenant les fichiers lore_*">
          <input type="text" value={folderPath} onChange={e => setFolderPath(e.target.value)}
            placeholder="C:\chemin\vers\api\data\files" className={inputClass} />
        </Field>
        <div className="flex items-center gap-3">
          <button onClick={handleTriggerIngest}
            disabled={ingestState === "running" || !folderPath.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150">
            {ingestState === "running"
              ? <><Loader2 size={13} className="animate-spin" /> En cours…</>
              : <><Play size={13} /> Lancer l'ingestion</>}
          </button>
          {ingestState !== "idle" && (
            <div className={clsx("flex items-center gap-1.5 text-sm animate-fade-in",
              ingestState === "success" && "text-green-400",
              ingestState === "error"   && "text-red-400",
              ingestState === "running" && "text-muted-fg",
            )}>
              {ingestState === "success" && <CheckCircle size={13} />}
              {ingestState === "error"   && <XCircle size={13} />}
              {ingestState === "running" && <Loader2 size={13} className="animate-spin" />}
              <span className="text-xs">{ingestMsg}</span>
            </div>
          )}
        </div>
      </Section>

    </div>
  );
}