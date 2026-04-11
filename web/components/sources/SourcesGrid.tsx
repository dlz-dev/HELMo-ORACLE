"use client";

import { useEffect, useState } from "react";
import { FileText, Hash, Calendar, RefreshCw, ChevronRight } from "lucide-react";
import { getSources } from "@/lib/api";
import type { Source } from "@/lib/api";
import { clsx } from "clsx";

export function SourcesGrid() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

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

  const toggleExpand = (source: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(source)) next.delete(source);
      else next.add(source);
      return next;
    });
  };

  useEffect(() => {
    fetchSources();
  }, []);

  // Groupement par jour
  const groupedSources = sources.reduce((acc: Record<string, Source[]>, s) => {
    const dateStr = s.ingested_at.split(" ")[0]; // Récupère YYYY-MM-DD
    if (!acc[dateStr]) acc[dateStr] = [];
    acc[dateStr].push(s);
    return acc;
  }, {});

  const sortedDates = Object.keys(groupedSources).sort((a, b) => b.localeCompare(a));

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat("fr-FR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(date);
  };

  if (loading)
    return (
      <div className="space-y-8">
        {[...Array(2)].map((_, groupIdx) => (
          <div key={groupIdx} className="space-y-4">
            <div className="h-6 w-48 bg-subtle rounded animate-pulse" />
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="h-24 rounded-xl bg-subtle animate-pulse"
                />
              ))}
            </div>
          </div>
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
      <div className="py-16 text-center text-muted-fg text-sm bg-surface border border-dashed border-default rounded-2xl">
        Aucune archive trouvée. Lance une ingestion depuis la page Admin.
      </div>
    );

  return (
    <div className="space-y-10">
      {sortedDates.map((dateStr) => (
        <section key={dateStr} className="space-y-4">
          <div className="flex items-center gap-3 px-1">
            <h2 className="text-sm font-oracle font-semibold text-gold tracking-widest uppercase">
              {formatDate(dateStr)}
            </h2>
            <div className="h-px flex-1 bg-gradient-to-r from-gold/20 to-transparent" />
          </div>

          <div className="space-y-3">
            {groupedSources[dateStr].map((s, i) => {
              const isExpanded = expandedSources.has(s.source);
              const canExpand = s.global_context && s.global_context.length > 150;

              return (
                <div
                  key={s.source}
                  onClick={() => canExpand && toggleExpand(s.source)}
                  className={clsx(
                    "group relative flex flex-col md:flex-row md:items-start gap-4 p-5 rounded-2xl border border-default bg-surface transition-all duration-300 animate-fade-up",
                    canExpand ? "cursor-pointer hover:border-gold/30 hover:shadow-card hover:bg-subtle/30" : "cursor-default",
                    isExpanded ? "border-gold/20 bg-subtle/20 shadow-sm" : ""
                  )}
                  style={{ animationDelay: `${i * 40}ms` }}
                >
                  {/* Icône Document */}
                  <div
                    className="flex-shrink-0 w-12 h-14 rounded-lg bg-gradient-to-br from-gold-glow to-transparent border border-gold/10
                                  flex flex-col items-center justify-center gap-1 relative overflow-hidden mt-1"
                  >
                    <FileText size={20} className="text-gold opacity-80" />
                    <div className="absolute top-0 right-0 w-4 h-4 bg-gold/10 rounded-bl-lg border-b border-l border-gold/20" />
                  </div>

                  {/* Infos principales */}
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-medium text-main truncate group-hover:text-gold transition-colors">
                        {s.source}
                      </h3>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-subtle border border-default text-[10px] font-medium text-muted-fg">
                          <Hash size={10} />
                          {s.chunk_count} chunks
                        </span>
                      </div>
                    </div>

                    {/* Contexte Global */}
                    <div className="relative">
                      <p className={clsx(
                        "text-sm text-muted-fg leading-relaxed transition-all duration-300",
                        !isExpanded && canExpand ? "line-clamp-2" : ""
                      )}>
                        {s.global_context && s.global_context !== "Aucun contexte global disponible." 
                          ? s.global_context 
                          : "Aucune description détaillée disponible pour cette archive."}
                      </p>
                      {canExpand && (
                        <div className="mt-2 text-[10px] font-semibold text-gold uppercase tracking-widest flex items-center gap-1 opacity-70 group-hover:opacity-100 transition-opacity">
                          {isExpanded ? "Réduire" : "Cliquer pour voir tout le contexte"}
                          <ChevronRight size={10} className={clsx("transition-transform duration-300", isExpanded ? "rotate-90" : "")} />
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Heure et Date */}
                  <div className="flex items-center justify-between md:flex-col md:items-end gap-2 shrink-0 border-t md:border-t-0 border-default pt-3 md:pt-1">
                    <span className="flex items-center gap-1 text-[10px] text-subtle-fg font-mono uppercase">
                      <Calendar size={10} />
                      {s.ingested_at.split(" ")[1]} {s.ingested_at.split(" ")[2]}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
