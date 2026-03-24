"use client";

import { Play, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { Section, Field, inputClass } from "./shared";
import type { IngestStatus } from "@/lib/api";

interface Props {
  files: FileList | null;
  ingestState: IngestStatus["last_status"];
  ingestMsg: string;
  onFilesChange: (files: FileList | null) => void;
  onIngest: () => void;
}

export function IngestSection({
  files,
  ingestState,
  ingestMsg,
  onFilesChange,
  onIngest,
}: Props) {
  return (
    <Section title="Ingestion">
      <Field
        label="Sélectionner un dossier"
        hint="Navigue jusqu'au dossier contenant tes fichiers lore_*"
      >
        <input
          type="file"
          // @ts-ignore
          webkitdirectory=""
          multiple
          onChange={(e) => onFilesChange(e.target.files)}
          className={inputClass}
        />
      </Field>
      {files && files.length > 0 && (
        <p className="text-xs text-muted-fg">
          {files.length} fichier(s) sélectionné(s)
        </p>
      )}
      <div className="flex items-center gap-3">
        <button
          onClick={onIngest}
          disabled={ingestState === "running" || !files || files.length === 0}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
        >
          {ingestState === "running" ? (
            <>
              <Loader2 size={13} className="animate-spin" /> En cours…
            </>
          ) : (
            <>
              <Play size={13} /> Lancer l'ingestion
            </>
          )}
        </button>
        {ingestState !== "idle" && ingestState !== "running" && (
          <div
            className={clsx(
              "flex items-center gap-1.5 text-sm animate-fade-in",
              ingestState === "success" && "text-green-400",
              ingestState === "warning" && "text-yellow-400",
              ingestState === "error" && "text-red-400",
            )}
          >
            {ingestState === "success" && <CheckCircle size={13} />}
            {ingestState === "warning" && <XCircle size={13} />}
            {ingestState === "error" && <XCircle size={13} />}
            <span className="text-xs">{ingestMsg}</span>
          </div>
        )}
      </div>
    </Section>
  );
}