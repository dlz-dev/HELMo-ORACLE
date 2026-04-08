"use client";

import { useState, useEffect } from "react";
import {
  Lock,
  Eye,
  EyeOff,
  LayoutDashboard,
  Upload,
  Settings2,
  FileText,
  Activity,
  LogOut,
  Unlock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Database,
  Cpu,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { IngestStatus } from "@/lib/api";

import { LS } from "./sections/shared";
import { ModelSection } from "./sections/ModelSection";
import { LogsSection } from "./sections/LogsSection";
import { HealthSection } from "./sections/HealthSection";
import { IngestSection } from "./sections/IngestSection";

const NAV = [
  { id: "overview", label: "Tableau de bord", icon: LayoutDashboard },
  { id: "ingest", label: "Ingestion", icon: Upload },
  { id: "config", label: "Configuration", icon: Settings2 },
  { id: "logs", label: "Journaux", icon: FileText },
  { id: "health", label: "Santé système", icon: Activity },
] as const;

type Tab = (typeof NAV)[number]["id"];

export function AdminPanel() {
  // ── Auth ──────────────────────────────────────────────────────────
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState(false);

  // ── Navigation ────────────────────────────────────────────────────
  const [tab, setTab] = useState<Tab>("overview");

  // ── Config IA ─────────────────────────────────────────────────────
  const [provider, setProvider] = useState("groq");
  const [model, setModel] = useState("llama-3.3-70b-versatile");
  const [temperature, setTemperature] = useState(0);
  const [kFinal, setKFinal] = useState(5);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved">("idle");

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
  const [ingestFiles, setIngestFiles] = useState<IngestStatus["files"]>({});

  // ── Init localStorage ─────────────────────────────────────────────
  useEffect(() => {
    setProvider(localStorage.getItem(LS.provider) || "groq");
    setModel(localStorage.getItem(LS.model) || "llama-3.3-70b-versatile");
    setTemperature(parseFloat(localStorage.getItem(LS.temperature) || "0"));
    setKFinal(parseInt(localStorage.getItem(LS.k_final) || "5"));
  }, []);

  // ── Auto health check on overview ────────────────────────────────
  useEffect(() => {
    if (
      tab === "overview" &&
      unlocked &&
      !healthData &&
      healthState === "idle"
    ) {
      handleHealthCheck();
    }
  }, [tab, unlocked]);

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

  const handleCancelIngest = async () => {
    try {
      await fetch("/api/admin/ingest/cancel", { method: "POST" });
    } catch {}
    setIngestState("warning");
    setIngestMsg("Ingestion annulée par l'administrateur.");
  };

  const handleHealthCheck = async () => {
    setHealthState("running");
    setHealthData(null);
    try {
      const res = await fetch("/api/admin/health");
      setHealthData(await res.json());
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
      let pollErrors = 0;
      const poll = setInterval(async () => {
        try {
          const r = await fetch("/api/admin/ingest/status");
          const status = await r.json();
          pollErrors = 0;
          setIngestMsg(status.last_message || "En cours…");
          setIngestFiles(status.files ?? {});
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
          if (++pollErrors >= 5) {
            clearInterval(poll);
            setIngestState("error");
            setIngestMsg("Impossible de joindre le backend.");
          }
        }
      }, 2000);
    } catch (e: any) {
      setIngestState("error");
      setIngestMsg(e.message);
    }
  };

  // ── Lock screen ───────────────────────────────────────────────────
  if (!unlocked) {
    return (
      <div className="flex items-center justify-center h-full bg-[var(--bg)] animate-fade-in">
        <Card className="w-full max-w-sm border-[var(--border)] bg-[var(--surface)] shadow-lg">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto w-12 h-12 rounded-full bg-[var(--gold-glow)] border border-[var(--gold)]/20 flex items-center justify-center mb-3">
              <Lock size={20} className="text-[var(--gold)]" />
            </div>
            <CardTitle className="font-cinzel text-[var(--text)] tracking-widest text-base uppercase">
              Administration
            </CardTitle>
            <p className="text-xs text-[var(--text-subtle)]">
              Accès réservé aux administrateurs
            </p>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                placeholder="Mot de passe admin"
                className={cn(
                  "pr-10 bg-[var(--bg-subtle)] border-[var(--border)] text-[var(--text)] placeholder:text-[var(--text-subtle)]",
                  authError && "border-red-400/60",
                )}
              />
              <button
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-subtle)] hover:text-[var(--text)]"
              >
                {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            {authError && (
              <p className="text-xs text-red-400 text-center">
                Mot de passe incorrect
              </p>
            )}
            <Button
              onClick={handleLogin}
              className="w-full bg-[var(--gold)] hover:bg-[var(--gold-light)] text-[#0a0c10] font-medium"
            >
              Accéder au tableau de bord
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Helper: global health badge ───────────────────────────────────
  const overallStatus = healthData?.status;
  const StatusBadge = () => {
    if (!healthData) return null;
    if (overallStatus === "ok")
      return (
        <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/20 text-[10px]">
          Opérationnel
        </Badge>
      );
    if (overallStatus === "degraded")
      return (
        <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/20 text-[10px]">
          Dégradé
        </Badge>
      );
    return (
      <Badge className="bg-red-500/15 text-red-400 border-red-500/20 text-[10px]">
        Erreur
      </Badge>
    );
  };

  return (
    <div className="flex h-full bg-[var(--bg)]">
      {/* ── Sidebar ────────────────────────────────────────────────── */}
      <aside className="flex flex-col w-14 md:w-56 border-r border-[var(--border)] bg-[var(--surface)] shrink-0">
        {/* Logo */}
        <div className="px-3 py-4 border-b border-[var(--border)] flex items-center gap-3">
          <span className="text-[var(--gold)] text-lg shrink-0">◈</span>
          <span className="hidden md:block font-cinzel text-xs text-[var(--gold)] tracking-widest uppercase truncate">
            Oracle Admin
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2 space-y-0.5 px-1.5">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                "w-full flex items-center gap-3 px-2 py-2.5 rounded-md text-sm transition-all duration-150",
                tab === id
                  ? "bg-[var(--gold-glow)] text-[var(--gold)] border border-[var(--gold)]/20"
                  : "text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-subtle)]",
              )}
            >
              <Icon size={16} className="shrink-0" />
              <span className="hidden md:block truncate">{label}</span>
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-2 border-t border-[var(--border)]">
          <button
            onClick={() => setUnlocked(false)}
            className="w-full flex items-center gap-3 px-2 py-2 rounded-md text-xs text-[var(--text-subtle)] hover:text-red-400 transition-colors"
          >
            <LogOut size={14} className="shrink-0" />
            <span className="hidden md:block">Déconnexion</span>
          </button>
        </div>
      </aside>

      {/* ── Main content ───────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-[var(--border)] bg-[var(--surface)] shrink-0">
          <div>
            <h1 className="text-sm font-medium text-[var(--text)]">
              {NAV.find((n) => n.id === tab)?.label}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge />
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <Unlock size={11} />
              <span className="hidden sm:block">Session active</span>
            </div>
          </div>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto p-6">
          {/* ── OVERVIEW ─────────────────────────────────────────── */}
          {tab === "overview" && (
            <div className="space-y-6 max-w-5xl mx-auto">
              {/* Stats cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* Santé système */}
                <Card className="border-[var(--border)] bg-[var(--surface)]">
                  <CardContent className="pt-5 pb-4 px-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-xs text-[var(--text-subtle)] uppercase tracking-wider mb-1">
                          Santé système
                        </p>
                        {healthState === "running" ? (
                          <p className="text-sm text-[var(--text-muted)] animate-pulse">
                            Vérification…
                          </p>
                        ) : healthData ? (
                          <div className="space-y-1">
                            {overallStatus === "ok" && (
                              <p className="text-sm font-medium text-emerald-400">
                                Opérationnel
                              </p>
                            )}
                            {overallStatus === "degraded" && (
                              <p className="text-sm font-medium text-amber-400">
                                Dégradé
                              </p>
                            )}
                            {overallStatus === "error" && (
                              <p className="text-sm font-medium text-red-400">
                                Erreur détectée
                              </p>
                            )}
                            <p className="text-[10px] text-[var(--text-subtle)]">
                              {Object.keys(healthData.checks || {}).length}{" "}
                              services vérifiés
                            </p>
                          </div>
                        ) : (
                          <p className="text-sm text-[var(--text-muted)]">
                            Non vérifié
                          </p>
                        )}
                      </div>
                      <div
                        className={cn(
                          "p-2 rounded-lg",
                          overallStatus === "ok"
                            ? "bg-emerald-500/10"
                            : overallStatus === "degraded"
                              ? "bg-amber-500/10"
                              : "bg-[var(--bg-subtle)]",
                        )}
                      >
                        {overallStatus === "ok" ? (
                          <CheckCircle2
                            size={18}
                            className="text-emerald-400"
                          />
                        ) : overallStatus === "degraded" ? (
                          <AlertTriangle size={18} className="text-amber-400" />
                        ) : (
                          <Activity
                            size={18}
                            className="text-[var(--text-muted)]"
                          />
                        )}
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        handleHealthCheck();
                        setTab("health");
                      }}
                      className="mt-3 h-7 text-xs w-full border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)]"
                    >
                      Vérifier
                    </Button>
                  </CardContent>
                </Card>

                {/* Provider actif */}
                <Card className="border-[var(--border)] bg-[var(--surface)]">
                  <CardContent className="pt-5 pb-4 px-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-xs text-[var(--text-subtle)] uppercase tracking-wider mb-1">
                          Provider actif
                        </p>
                        <p className="text-sm font-medium text-[var(--text)] capitalize">
                          {provider}
                        </p>
                        <p className="text-[10px] text-[var(--text-subtle)] truncate max-w-[140px] mt-0.5">
                          {model}
                        </p>
                      </div>
                      <div className="p-2 rounded-lg bg-[var(--gold-glow)]">
                        <Cpu size={18} className="text-[var(--gold)]" />
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setTab("config")}
                      className="mt-3 h-7 text-xs w-full border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)]"
                    >
                      Configurer
                    </Button>
                  </CardContent>
                </Card>

                {/* Base de données */}
                <Card className="border-[var(--border)] bg-[var(--surface)]">
                  <CardContent className="pt-5 pb-4 px-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-xs text-[var(--text-subtle)] uppercase tracking-wider mb-1">
                          Base vectorielle
                        </p>
                        {healthData?.checks?.database?.documents !==
                        undefined ? (
                          <>
                            <p className="text-sm font-medium text-[var(--text)]">
                              {healthData.checks.database.documents.toLocaleString(
                                "fr",
                              )}{" "}
                              fichiers
                            </p>
                            <p className="text-[10px] text-[var(--text-subtle)] mt-0.5">
                              {healthData.checks.database.latency_ms}ms latence
                            </p>
                          </>
                        ) : (
                          <p className="text-sm text-[var(--text-muted)]">—</p>
                        )}
                      </div>
                      <div className="p-2 rounded-lg bg-[var(--bg-subtle)]">
                        <Database
                          size={18}
                          className="text-[var(--text-muted)]"
                        />
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setTab("ingest")}
                      className="mt-3 h-7 text-xs w-full border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)]"
                    >
                      Ingestion
                    </Button>
                  </CardContent>
                </Card>
              </div>

              {/* Quick actions */}
              <Card className="border-[var(--border)] bg-[var(--surface)]">
                <CardHeader className="pb-3 pt-4 px-5">
                  <CardTitle className="text-sm text-[var(--text)]">
                    Accès rapide
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-5">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {NAV.filter((n) => n.id !== "overview").map(
                      ({ id, label, icon: Icon }) => (
                        <button
                          key={id}
                          onClick={() => setTab(id)}
                          className="flex flex-col items-center gap-2 p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-subtle)] hover:border-[var(--gold)]/30 hover:bg-[var(--gold-glow)] transition-all duration-150"
                        >
                          <Icon
                            size={20}
                            className="text-[var(--text-muted)]"
                          />
                          <span className="text-xs text-[var(--text-muted)]">
                            {label}
                          </span>
                        </button>
                      ),
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Services detail */}
              {healthData && (
                <Card className="border-[var(--border)] bg-[var(--surface)]">
                  <CardHeader className="pb-3 pt-4 px-5">
                    <CardTitle className="text-sm text-[var(--text)]">
                      Services
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-5 pb-5">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {Object.entries(healthData.checks || {}).map(
                        ([key, val]: [string, any]) => (
                          <div
                            key={key}
                            className={cn(
                              "flex items-center justify-between px-3 py-2.5 rounded-lg text-xs border",
                              val.status === "ok"
                                ? "bg-emerald-500/8 border-emerald-500/20 text-emerald-300"
                                : val.status === "error"
                                  ? "bg-red-500/8 border-red-500/20 text-red-300"
                                  : "bg-[var(--bg-subtle)] border-[var(--border)] text-[var(--text-muted)]",
                            )}
                          >
                            <div className="flex items-center gap-2">
                              {val.status === "ok" && (
                                <CheckCircle2 size={12} />
                              )}
                              {val.status === "error" && <XCircle size={12} />}
                              {val.status === "not_configured" && (
                                <div className="w-3 h-3 rounded-full border border-current opacity-40" />
                              )}
                              <span className="font-medium capitalize">
                                {key}
                              </span>
                            </div>
                            <span className="opacity-70">
                              {val.latency_ms
                                ? `${val.latency_ms}ms`
                                : val.documents !== undefined
                                  ? `${val.documents} fichiers`
                                  : val.status === "not_configured"
                                    ? "Non configuré"
                                    : val.error
                                      ? val.error.slice(0, 30)
                                      : ""}
                            </span>
                          </div>
                        ),
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* ── INGESTION ────────────────────────────────────────────── */}
          {tab === "ingest" && (
            <div className="max-w-3xl mx-auto">
              <IngestSection
                files={files}
                ingestState={ingestState}
                ingestMsg={ingestMsg}
                ingestFiles={ingestFiles}
                onFilesChange={setFiles}
                onIngest={handleTriggerIngest}
                onCancel={handleCancelIngest}
              />
            </div>
          )}

          {/* ── CONFIG ───────────────────────────────────────────────── */}
          {tab === "config" && (
            <div className="max-w-3xl mx-auto space-y-4">
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
            </div>
          )}

          {/* ── LOGS ─────────────────────────────────────────────────── */}
          {tab === "logs" && (
            <div className="max-w-5xl mx-auto">
              <LogsSection />
            </div>
          )}

          {/* ── HEALTH ───────────────────────────────────────────────── */}
          {tab === "health" && (
            <div className="max-w-3xl mx-auto">
              <HealthSection
                healthData={healthData}
                healthState={healthState}
                onCheck={handleHealthCheck}
              />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
