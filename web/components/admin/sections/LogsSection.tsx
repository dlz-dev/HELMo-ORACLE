"use client";

import { useRef } from "react";
import { Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { Section } from "./shared";

interface Props {
  logs: string[];
  logsLoading: boolean;
  autoRefresh: boolean;
  onFetch: () => void;
  onToggleAutoRefresh: () => void;
  onClear: () => void;
}

export function LogsSection({
  logs,
  logsLoading,
  autoRefresh,
  onFetch,
  onToggleAutoRefresh,
  onClear,
}: Props) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  return (
    <Section title="Logs système" defaultOpen={false}>
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={onFetch}
          disabled={logsLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gold text-white text-xs font-medium hover:bg-gold-light disabled:opacity-40 transition-colors"
        >
          {logsLoading ? (
            <>
              <Loader2 size={11} className="animate-spin" /> Chargement…
            </>
          ) : (
            "🔄 Actualiser"
          )}
        </button>
        <button
          onClick={onToggleAutoRefresh}
          className={clsx(
            "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
            autoRefresh
              ? "bg-green-400/20 border-green-400/40 text-green-300"
              : "border-default text-muted-fg hover:text-main",
          )}
        >
          {autoRefresh ? "⏸ Auto-refresh ON" : "▶ Auto-refresh OFF"}
        </button>
        <button
          onClick={onClear}
          className="px-3 py-1.5 rounded-lg text-xs font-medium border border-red-400/30 text-red-400 hover:bg-red-400/10 transition-colors ml-auto"
        >
          🗑 Vider les logs
        </button>
      </div>

      <div className="bg-[#0a0c10] rounded-lg border border-default overflow-auto h-64 p-3 font-mono text-xs">
        {logs.length === 0 ? (
          <p className="text-muted-fg">Aucun log — cliquez sur Actualiser</p>
        ) : (
          logs.map((line, i) => (
            <div
              key={`log-${i}`}
              className={clsx(
                "leading-5",
                line.includes("ERROR") && "text-red-400",
                line.includes("WARNING") && "text-amber-400",
                line.includes("INFO") && "text-green-300",
                !line.includes("ERROR") &&
                  !line.includes("WARNING") &&
                  !line.includes("INFO") &&
                  "text-muted-fg",
              )}
            >
              {line}
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </Section>
  );
}
