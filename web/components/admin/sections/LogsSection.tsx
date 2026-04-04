"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Loader2,
  AlertTriangle,
  Info,
  XCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { clsx } from "clsx";
import { Section } from "./shared";

interface LogEntry {
  id: string;
  created_at: string;
  level: "INFO" | "WARNING" | "ERROR";
  source: string;
  message: string;
  metadata?: Record<string, any>;
  profiles?: { first_name: string; last_name: string } | null;
}

const PAGE_SIZE = 15;

const levelConfig = {
  ERROR: {
    icon: XCircle,
    color: "text-red-400 bg-red-400/10 border-red-400/20",
  },
  WARNING: {
    icon: AlertTriangle,
    color: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  },
  INFO: { icon: Info, color: "text-sky-400 bg-sky-400/10 border-sky-400/20" },
};

export function LogsSection() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [levelFilter, setLevelFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [page, setPage] = useState(0);
  const [hasNext, setHasNext] = useState(false);

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      params.set("lines", String(PAGE_SIZE + 1)); // +1 pour détecter s'il y a une page suivante
      params.set("offset", String(page * PAGE_SIZE));
      if (levelFilter) params.set("level", levelFilter);
      if (sourceFilter) params.set("source", sourceFilter);

      try {
        const res = await fetch(`/api/admin/logs?${params.toString()}`);
        if (!res.ok) {
          const data = await res.json();
          throw new Error(
            data.error || "Erreur lors de la récupération des logs",
          );
        }
        const data = await res.json();
        const all: LogEntry[] = data.logs || [];
        setHasNext(all.length > PAGE_SIZE);
        setLogs(all.slice(0, PAGE_SIZE));
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [page, levelFilter, sourceFilter]);

  // Reset page quand les filtres changent
  function handleLevelFilter(v: string) {
    setLevelFilter(v);
    setPage(0);
  }
  function handleSourceFilter(v: string) {
    setSourceFilter(v);
    setPage(0);
  }

  return (
    <Section title="Logs Système" defaultOpen={true}>
      {/* Filtres */}
      <div className="flex items-center gap-3 mb-4">
        <select
          value={levelFilter}
          onChange={(e) => handleLevelFilter(e.target.value)}
          className="bg-subtle border border-default rounded-md px-2 py-1 text-xs"
        >
          <option value="">Tous les niveaux</option>
          <option value="ERROR">Error</option>
          <option value="WARNING">Warning</option>
          <option value="INFO">Info</option>
        </select>
        <input
          type="text"
          value={sourceFilter}
          onChange={(e) => handleSourceFilter(e.target.value)}
          placeholder="Filtrer par source…"
          className="bg-subtle border border-default rounded-md px-2 py-1 text-xs w-40 focus:outline-none focus:border-gold/50"
        />
      </div>

      {/* Tableau */}
      <div className="overflow-x-auto border border-default rounded-lg bg-surface">
        <table className="min-w-full divide-y divide-default text-sm">
          <thead className="bg-subtle">
            <tr>
              <th className="px-4 py-2 text-left font-semibold">Date</th>
              <th className="px-4 py-2 text-left font-semibold">Niveau</th>
              <th className="px-4 py-2 text-left font-semibold">Source</th>
              <th className="px-4 py-2 text-left font-semibold">Utilisateur</th>
              <th className="px-4 py-2 text-left font-semibold">Message</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-default">
            {loading ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-muted-fg">
                  <Loader2 className="mx-auto animate-spin" />
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-red-400">
                  {error}
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-muted-fg">
                  Aucun log trouvé.
                </td>
              </tr>
            ) : (
              logs.map((log) => {
                const config = levelConfig[log.level] || levelConfig.INFO;
                const Icon = config.icon;
                const user = log.profiles
                  ? `${log.profiles.first_name} ${log.profiles.last_name}`.trim()
                  : "Système";

                return (
                  <tr key={log.id}>
                    <td className="px-4 py-2 whitespace-nowrap text-muted-fg">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={clsx(
                          "flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border",
                          config.color,
                        )}
                      >
                        <Icon size={12} />
                        {log.level}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">
                      {log.source}
                    </td>
                    <td className="px-4 py-2 text-muted-fg">{user}</td>
                    <td className="px-4 py-2">
                      <p>{log.message}</p>
                      {log.metadata && (
                        <pre className="mt-2 p-2 bg-black/20 rounded-md text-xs text-muted-fg overflow-x-auto">
                          {JSON.stringify(log.metadata, null, 2)}
                        </pre>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-muted-fg">Page {page + 1}</span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p - 1)}
            disabled={page === 0 || loading}
            className="h-7 px-2 text-xs border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)] hover:border-[var(--gold)]/40 disabled:opacity-30"
          >
            <ChevronLeft size={13} /> Précédent
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasNext || loading}
            className="h-7 px-2 text-xs border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)] hover:border-[var(--gold)]/40 disabled:opacity-30"
          >
            Suivant <ChevronRight size={13} />
          </Button>
        </div>
      </div>
    </Section>
  );
}
