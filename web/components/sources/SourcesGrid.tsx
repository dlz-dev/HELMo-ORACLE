"use client";

import { useEffect, useState } from "react";
import { FileText, Hash, Calendar, RefreshCw } from "lucide-react";
import { getSources } from "@/lib/api";
import type { Source } from "@/lib/api";

export function SourcesGrid() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const sourceData = await getSources();
      setSources(sourceData);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  if (loading)
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="h-36 rounded-xl bg-subtle animate-pulse"
            style={{ animationDelay: `${i * 80}ms` }}
          />
        ))}
      </div>
    );

  if (error)
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-muted-fg">
        <p className="text-sm">{error}</p>
        <button
          onClick={fetchSources}
          className="flex items-center gap-1.5 text-sm text-gold hover:underline"
        >
          <RefreshCw size={13} /> Réessayer
        </button>
      </div>
    );

  if (sources.length === 0)
    return (
      <div className="py-16 text-center text-muted-fg text-sm">
        Aucune archive trouvée. Lance une ingestion depuis la page Admin.
      </div>
    );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {sources.map((s, i) => (
        <div
          key={s.source}
          className="group rounded-xl border border-default bg-surface p-4
                     hover:border-gold/30 hover:shadow-card
                     transition-all duration-200 animate-fade-up"
          style={{ animationDelay: `${i * 50}ms` }}
        >
          {/* En-tête */}
          <div className="flex items-start gap-2.5 mb-3">
            <div
              className="flex-shrink-0 w-8 h-8 rounded-lg bg-gold-glow border border-gold/20
                            flex items-center justify-center mt-0.5"
            >
              <FileText size={14} className="text-gold" />
            </div>
            <div className="min-w-0">
              <p
                className="text-sm font-medium text-main truncate"
                title={s.source}
              >
                {s.source}
              </p>
              <div className="flex items-center gap-3 mt-0.5">
                <span className="flex items-center gap-1 text-xs text-subtle-fg">
                  <Hash size={10} />
                  {s.chunk_count} chunks
                </span>
                <span className="flex items-center gap-1 text-xs text-subtle-fg">
                  <Calendar size={10} />
                  {s.ingested_at}
                </span>
              </div>
            </div>
          </div>

          {/* Contexte global */}
          {s.global_context &&
            s.global_context !== "Aucun contexte disponible." && (
              <p className="text-xs text-muted-fg leading-relaxed line-clamp-3 border-t border-subtle pt-3">
                {s.global_context}
              </p>
            )}
        </div>
      ))}
    </div>
  );
}
