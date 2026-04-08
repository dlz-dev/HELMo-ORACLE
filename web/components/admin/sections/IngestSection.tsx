"use client";

import { useRef } from "react";
import {
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  FileText,
  FolderOpen,
  StopCircle,
  Shield,
  FileSearch,
  Sparkles,
  Layers,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Progress,
  ProgressTrack,
  ProgressIndicator,
} from "@/components/ui/progress";
import type { IngestStatus, FileIngestStatus } from "@/lib/api";

interface Props {
  files: FileList | null;
  ingestState: IngestStatus["last_status"];
  ingestMsg: string;
  ingestFiles?: IngestStatus["files"];
  onFilesChange: (files: FileList | null) => void;
  onIngest: () => void;
  onCancel: () => void;
}

const FILE_STATUS_META: Record<
  FileIngestStatus,
  { label: string; color: string; icon: React.ElementType; spin?: boolean }
> = {
  pending:        { label: "En attente",      color: "text-[var(--text-subtle)]",  icon: Clock },
  validating:     { label: "Validation",      color: "text-amber-400",             icon: Shield,     spin: true },
  converting:     { label: "Conversion",      color: "text-blue-400",              icon: FileSearch, spin: true },
  contextualizing:{ label: "Contextualisation",color: "text-purple-400",           icon: Sparkles,   spin: true },
  vectorizing:    { label: "Vectorisation",   color: "text-[var(--gold)]",         icon: Layers,     spin: true },
  done:           { label: "Terminé",         color: "text-emerald-400",           icon: CheckCircle2 },
  rejected:       { label: "Rejeté",          color: "text-red-400",               icon: XCircle },
};

function parseProgress(
  files: IngestStatus["files"],
  isRunning: boolean,
  isDone: boolean,
): number {
  if (isDone) return 100;
  if (!isRunning || !files) return 5;
  const entries = Object.values(files);
  if (entries.length === 0) return 5;
  const weight: Record<FileIngestStatus, number> = {
    pending: 0, validating: 1, converting: 2, contextualizing: 3, vectorizing: 4, done: 5, rejected: 5,
  };
  const total = entries.length * 5;
  const done = entries.reduce((sum, s) => sum + (weight[s] ?? 0), 0);
  return Math.min(Math.round((done / total) * 95) + 5, 98);
}

export function IngestSection({
  files,
  ingestState,
  ingestMsg,
  ingestFiles = {},
  onFilesChange,
  onIngest,
  onCancel,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const isRunning = ingestState === "running";
  const isDone = ["success", "warning", "error"].includes(ingestState);
  const progress = parseProgress(ingestFiles, isRunning, isDone);
  const fileEntries = Object.entries(ingestFiles ?? {});

  return (
    <div className="space-y-5">
      {/* Drop zone / file picker */}
      <Card className="border-[var(--border)] bg-[var(--surface)]">
        <CardHeader className="pb-2 pt-4 px-5">
          <CardTitle className="text-sm text-[var(--text)]">
            Sélection des fichiers
          </CardTitle>
        </CardHeader>
        <CardContent className="px-5 pb-5 space-y-4">
          {/* Click-to-select area */}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={isRunning}
            className={cn(
              "w-full border-2 border-dashed rounded-xl p-8 flex flex-col items-center gap-3 transition-all duration-200",
              files && files.length > 0
                ? "border-[var(--gold)]/40 bg-[var(--gold-glow)]"
                : "border-[var(--border)] bg-[var(--bg-subtle)] hover:border-[var(--gold)]/30 hover:bg-[var(--gold-glow)]",
              isRunning && "opacity-50 cursor-not-allowed",
            )}
          >
            <div
              className={cn(
                "p-3 rounded-full",
                files && files.length > 0
                  ? "bg-[var(--gold)]/10"
                  : "bg-[var(--bg-muted)]",
              )}
            >
              <FolderOpen
                size={24}
                className={
                  files && files.length > 0
                    ? "text-[var(--gold)]"
                    : "text-[var(--text-subtle)]"
                }
              />
            </div>
            {files && files.length > 0 ? (
              <>
                <p className="text-sm font-medium text-[var(--text)]">
                  {files.length} fichier{files.length > 1 ? "s" : ""}{" "}
                  sélectionné{files.length > 1 ? "s" : ""}
                </p>
                <p className="text-xs text-[var(--text-subtle)]">
                  Cliquer pour changer le dossier
                </p>
              </>
            ) : (
              <>
                <p className="text-sm font-medium text-[var(--text)]">
                  Sélectionner un dossier
                </p>
                <p className="text-xs text-[var(--text-subtle)]">
                  Fichiers lore_* · CSV, PDF, TXT, MD, JSON
                </p>
              </>
            )}
          </button>

          {/* Hidden input */}
          <input
            ref={inputRef}
            type="file"
            // @ts-ignore
            webkitdirectory=""
            multiple
            className="hidden"
            onChange={(e) => onFilesChange(e.target.files)}
          />

          {/* File preview */}
          {files && files.length > 0 && !isRunning && (
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {Array.from(files)
                .slice(0, 8)
                .map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 px-2 py-1 rounded-md bg-[var(--bg-subtle)]"
                  >
                    <FileText
                      size={12}
                      className="text-[var(--text-subtle)] shrink-0"
                    />
                    <span className="text-xs text-[var(--text-muted)] truncate">
                      {f.name}
                    </span>
                    <span className="text-[10px] text-[var(--text-subtle)] ml-auto shrink-0">
                      {(f.size / 1024).toFixed(0)} KB
                    </span>
                  </div>
                ))}
              {files.length > 8 && (
                <p className="text-[10px] text-[var(--text-subtle)] text-center">
                  + {files.length - 8} autres fichiers
                </p>
              )}
            </div>
          )}

          {/* Launch button */}
          <Button
            onClick={onIngest}
            disabled={isRunning || !files || files.length === 0}
            className="w-full bg-[var(--gold)] hover:bg-[var(--gold-light)] text-[#0a0c10] font-medium disabled:opacity-40"
          >
            {isRunning ? (
              <>
                <Loader2 size={14} className="animate-spin mr-2" /> Ingestion en
                cours…
              </>
            ) : (
              <>
                <Upload size={14} className="mr-2" /> Lancer l'ingestion
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Progress section — visible during/after ingestion */}
      {(isRunning || isDone) && (
        <Card className="border-[var(--border)] bg-[var(--surface)] animate-fade-up">
          <CardHeader className="pb-3 pt-4 px-5">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm text-[var(--text)]">
                Progression
              </CardTitle>
              <div className="flex items-center gap-2">
                {isRunning && (
                  <>
                    <Badge className="bg-[var(--gold-glow)] text-[var(--gold)] border-[var(--gold)]/20 text-[10px] animate-pulse">
                      En cours
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={onCancel}
                      className="h-6 px-2 text-[10px] border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                    >
                      <StopCircle size={11} className="mr-1" /> Arrêter
                    </Button>
                  </>
                )}
                {ingestState === "success" && (
                  <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/20 text-[10px]">
                    Terminé
                  </Badge>
                )}
                {ingestState === "warning" && (
                  <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/20 text-[10px]">
                    Avertissement
                  </Badge>
                )}
                {ingestState === "error" && (
                  <Badge className="bg-red-500/15 text-red-400 border-red-500/20 text-[10px]">
                    Erreur
                  </Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-5 space-y-5">
            {/* Progress bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-[10px] text-[var(--text-subtle)]">
                <span>
                  {fileEntries.length > 0
                    ? `${fileEntries.filter(([, s]) => s === "done" || s === "rejected").length}/${fileEntries.length} fichiers`
                    : "Initialisation"}
                </span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} className="gap-0">
                <ProgressTrack className="h-1.5 bg-[var(--bg-muted)]">
                  <ProgressIndicator
                    className={cn(
                      "h-full transition-all duration-500",
                      ingestState === "success"
                        ? "bg-emerald-500"
                        : ingestState === "error"
                          ? "bg-red-500"
                          : "bg-[var(--gold)]",
                    )}
                  />
                </ProgressTrack>
              </Progress>
            </div>

            {/* Per-file parallel status */}
            {fileEntries.length > 0 && (
              <div className="space-y-1.5 max-h-64 overflow-y-auto">
                {fileEntries.map(([filename, status]) => {
                  const meta = FILE_STATUS_META[status] ?? FILE_STATUS_META.pending;
                  const Icon = meta.icon;
                  const isActive = !["done", "rejected", "pending"].includes(status);
                  return (
                    <div
                      key={filename}
                      className={cn(
                        "flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all duration-300 border",
                        isActive
                          ? "bg-[var(--gold-glow)] border-[var(--gold)]/20"
                          : status === "done"
                            ? "bg-emerald-500/5 border-emerald-500/15"
                            : status === "rejected"
                              ? "bg-red-500/5 border-red-500/15"
                              : "bg-[var(--bg-subtle)] border-transparent opacity-50",
                      )}
                    >
                      <Icon
                        size={13}
                        className={cn(meta.color, isActive && "animate-spin")}
                      />
                      <span className="text-xs text-[var(--text)] truncate flex-1 min-w-0">
                        {filename}
                      </span>
                      <span className={cn("text-[10px] shrink-0 font-medium", meta.color)}>
                        {meta.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Final message */}
            {isDone && (
              <div
                className={cn(
                  "flex items-start gap-3 p-3 rounded-lg text-sm",
                  ingestState === "success"
                    ? "bg-emerald-500/8 border border-emerald-500/20 text-emerald-300"
                    : ingestState === "warning"
                      ? "bg-amber-500/8 border border-amber-500/20 text-amber-300"
                      : "bg-red-500/8 border border-red-500/20 text-red-300",
                )}
              >
                {ingestState === "success" && (
                  <CheckCircle2 size={16} className="shrink-0 mt-0.5" />
                )}
                {ingestState === "warning" && (
                  <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                )}
                {ingestState === "error" && (
                  <XCircle size={16} className="shrink-0 mt-0.5" />
                )}
                <p className="text-xs leading-relaxed">{ingestMsg}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
