"use client";

import { useState, useEffect, useCallback } from "react";
import { Lock, Unlock, Eye, EyeOff } from "lucide-react";
import { clsx } from "clsx";
import type { IngestStatus } from "@/lib/api";

import { LS, inputClass } from "./sections/shared";
import { ModelSection } from "./sections/ModelSection";
import { ApiKeysSection } from "./sections/ApiKeysSection";
import { TestSection } from "./sections/TestSection";
import { LogsSection } from "./sections/LogsSection";
import { HealthSection } from "./sections/HealthSection";
import { IngestSection } from "./sections/IngestSection";

export function AdminPanel() {
  // ── Auth ─────────────────────────────────────────────────────────
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState(false);

  // ── Config IA ─────────────────────────────────────────────────────
  const [provider, setProvider] = useState("groq");
  const [model, setModel] = useState("llama-3.3-70b-versatile");
  const [temperature, setTemperature] = useState(0);
  const [kFinal, setKFinal] = useState(5);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved">("idle");

  // ── Clés API ──────────────────────────────────────────────────────
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({
    groq: "",
    openai: "",
    anthropic: "",
    gemini: "",
  });
  const [keySaveStatus, setKeySaveStatus] = useState<"idle" | "saved">("idle");

  // ── Test provider ─────────────────────────────────────────────────
  const [testMsg, setTestMsg] = useState("Dis-moi qui tu es en une phrase.");
  const [testState, setTestState] = useState<
    "idle" | "running" | "success" | "error"
  >("idle");
  const [testOutput, setTestOutput] = useState("");

  // ── Logs ──────────────────────────────────────────────────────────
  const [logs, setLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // ── Health ────────────────────────────────────────────────────────
  const [healthData, setHealthData] = useState<any>(null);
  const [healthState, setHealthState] = useState<"idle" | "running" | "done">(
    "idle",
  );

  // ── Ingestion ─────────────────────────────────────────────────────
  const [files, setFiles] = useState<FileList | null>(null);
  const [ingestState, setIngestState] =
    useState<IngestStatus["last_status"]>("idle");
  const [ingestMsg, setIngestMsg] = useState("");

  // ── Chargement localStorage ───────────────────────────────────────
  useEffect(() => {
    setProvider(localStorage.getItem(LS.provider) || "groq");
    setModel(localStorage.getItem(LS.model) || "llama-3.3-70b-versatile");
    setTemperature(parseFloat(localStorage.getItem(LS.temperature) || "0"));
    setKFinal(parseInt(localStorage.getItem(LS.k_final) || "5"));
    try {
      const saved = localStorage.getItem(LS.apiKeys);
      if (saved) setApiKeys(JSON.parse(saved));
    } catch {
      // JSON.parse peut échouer si la valeur localStorage est corrompue — on garde les défauts
    }
  }, []);

  // ── Auto-refresh logs ─────────────────────────────────────────────
  const fetchLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const res = await fetch("/api/admin/logs?lines=150");
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (err) {
      console.error("Erreur lors du chargement des logs:", err);
    } finally {
      setLogsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchLogs, 3000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchLogs]);

  // ── Handlers ─────────────────────────────────────────────────────
  const handleLogin = async () => {
    try {
      const res = await fetch("/api/admin/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        setUnlocked(true);
        setAuthError(false);
      } else setAuthError(true);
    } catch {
      setAuthError(true);
    }
  };

  const handleSaveConfig = () => {
    localStorage.setItem(LS.provider, provider);
    localStorage.setItem(LS.model, model);
    localStorage.setItem(LS.temperature, String(temperature));
    localStorage.setItem(LS.k_final, String(kFinal));
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
        body: JSON.stringify({
          provider,
          model,
          message: testMsg,
          temperature,
          k_final: 1,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setTestState("error");
        setTestOutput(`❌ ${data.error || data.detail || "Erreur inconnue"}`);
        return;
      }
      setTestState("success");
      setTestOutput(
        `✅ Provider: ${data.provider} · Modèle: ${data.model}\n\n${data.response}`,
      );
    } catch (e: any) {
      setTestState("error");
      setTestOutput(`❌ ${e.message}`);
    }
  };

  const handleHealthCheck = async () => {
    setHealthState("running");
    setHealthData(null);
    try {
      const res = await fetch("/api/admin/health");
      const data = await res.json();
      setHealthData(data);
    } catch (e: any) {
      setHealthData({
        status: "error",
        checks: { backend: { status: "error", error: e.message } },
      });
    } finally {
      setHealthState("done");
    }
  };

  const handleTriggerIngest = async () => {
    if (!files || files.length === 0) return;
    setIngestState("running");
    setIngestMsg("Envoi des fichiers…");
    try {
      const formData = new FormData();
      Array.from(files).forEach((f) => formData.append("files", f));
      const res = await fetch("/api/admin/ingest", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Erreur lors de l'envoi");
      const poll = setInterval(async () => {
        try {
          const r = await fetch("/api/admin/ingest/status");
          const status = await r.json();
          setIngestMsg(status.last_message || "En cours…");
          if (!status.running) {
            clearInterval(poll);
            setIngestState(
              status.last_status === "success"
                ? "success"
                : status.last_status === "warning"
                  ? "warning"
                  : "error",
            );
            setIngestMsg(status.last_message);
          }
        } catch {
          clearInterval(poll);
          setIngestState("error");
        }
      }, 2000);
    } catch (e: any) {
      setIngestState("error");
      setIngestMsg(e.message);
    }
  };

  // ── Écran de connexion ────────────────────────────────────────────
  if (!unlocked) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] animate-fade-in">
        <div className="w-full max-w-sm space-y-4">
          <div className="text-center mb-6">
            <Lock size={28} className="mx-auto text-gold mb-3" />
            <p className="text-sm text-muted-fg">
              Accès réservé aux administrateurs
            </p>
          </div>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              placeholder="Mot de passe admin"
              className={clsx(
                inputClass,
                "pr-10",
                authError && "border-red-400/50",
              )}
            />
            <button
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-subtle-fg hover:text-main"
            >
              {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          {authError && (
            <p className="text-xs text-red-400 text-center">
              Mot de passe incorrect
            </p>
          )}
          <button
            onClick={handleLogin}
            className="w-full py-2.5 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light transition-colors duration-150"
          >
            Accéder
          </button>
        </div>
      </div>
    );
  }

  // ── Panneau admin ─────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-sm text-green-400">
          <Unlock size={13} />
          <span>Session admin active</span>
        </div>
        <button
          onClick={() => setUnlocked(false)}
          className="text-xs text-muted-fg hover:text-main transition-colors"
        >
          Se déconnecter
        </button>
      </div>

      <ModelSection
        provider={provider}
        model={model}
        temperature={temperature}
        kFinal={kFinal}
        saveStatus={saveStatus}
        onProviderChange={setProvider}
        onModelChange={setModel}
        onTemperatureChange={setTemperature}
        onKFinalChange={setKFinal}
        onSave={handleSaveConfig}
      />
      <ApiKeysSection
        apiKeys={apiKeys}
        saveStatus={keySaveStatus}
        onChange={(p, v) => setApiKeys((k) => ({ ...k, [p]: v }))}
        onSave={handleSaveKeys}
      />
      <TestSection
        provider={provider}
        model={model}
        temperature={temperature}
        testMsg={testMsg}
        testState={testState}
        testOutput={testOutput}
        onMsgChange={setTestMsg}
        onTest={handleTestProvider}
      />
      <LogsSection
        logs={logs}
        logsLoading={logsLoading}
        autoRefresh={autoRefresh}
        onFetch={fetchLogs}
        onToggleAutoRefresh={() => setAutoRefresh((v) => !v)}
        onClear={async () => {
          await fetch("/api/admin/logs", { method: "DELETE" });
          setLogs([]);
        }}
      />
      <HealthSection
        healthData={healthData}
        healthState={healthState}
        onCheck={handleHealthCheck}
      />
      <IngestSection
        files={files}
        ingestState={ingestState}
        ingestMsg={ingestMsg}
        onFilesChange={setFiles}
        onIngest={handleTriggerIngest}
      />
    </div>
  );
}
