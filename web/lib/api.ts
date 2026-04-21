// ─── Types ────────────────────────────────────────────────────────
export interface Source {
  source: string;
  chunk_count: number;
  global_context: string;
  ingested_at: string;
}

export type FileIngestStatus =
  | "pending"
  | "validating"
  | "converting"
  | "contextualizing"
  | "vectorizing"
  | "done"
  | "rejected";

export interface IngestStatus {
  last_status: "idle" | "running" | "success" | "error" | "warning";
  last_message: string;
  running: boolean;
  files?: Record<string, FileIngestStatus>;
}

// ─── Fonctions API ──────────────────────────────────────────────────

/**
 * Déclenche le processus d'ingestion sur le serveur.
 */
export async function triggerIngest(folderPath: string): Promise<void> {
  const res = await fetch("/api/admin/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_path: folderPath }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Erreur inconnue lors de l'ingestion");
  }
}

/**
 * Récupère le statut actuel de l'ingestion.
 */
export async function getIngestStatus(): Promise<IngestStatus> {
  const res = await fetch("/api/admin/ingest/status");
  if (!res.ok) {
    throw new Error("Impossible de récupérer le statut de l'ingestion");
  }
  return res.json();
}

/**
 * Récupère la liste des sources de connaissance.
 */
export async function getSources(): Promise<Source[]> {
  const res = await fetch("/api/sources");
  if (!res.ok) {
    throw new Error("Impossible de charger les archives.");
  }
  const data = await res.json();
  return data.sources ?? [];
}

/**
 * Récupère le contenu brut d'un fichier source.
 */
export async function getSourceContent(filename: string): Promise<string> {
  const res = await fetch(`/api/sources/content/${encodeURIComponent(filename)}`);
  if (!res.ok) throw new Error("Fichier introuvable");
  return res.text();
}
