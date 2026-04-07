"use client";

import { Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { Section } from "./shared";
import { Button } from "@/components/ui/button";

interface Props {
  healthData: any;
  healthState: "idle" | "running" | "done";
  onCheck: () => void;
}

export function HealthSection({ healthData, healthState, onCheck }: Props) {
  return (
    <Section title="Health Check" defaultOpen={false}>
      <Button
        onClick={onCheck}
        disabled={healthState === "running"}
        className="w-full bg-[var(--gold)] hover:bg-[var(--gold-light)] text-[#0a0c10] text-sm font-medium disabled:opacity-40"
      >
        {healthState === "running" ? (
          <>
            <Loader2 size={13} className="animate-spin" /> Vérification en
            cours…
          </>
        ) : (
          <>🔍 Vérifier l'état du système</>
        )}
      </Button>

      {healthData && (
        <div className="space-y-2 mt-2">
          {Object.entries(healthData.checks || {}).map(
            ([key, val]: [string, any]) => (
              <div
                key={key}
                className={clsx(
                  "flex items-center justify-between px-3 py-2 rounded-lg text-xs border",
                  val.status === "ok" &&
                    "bg-green-400/10 border-green-400/30 text-green-300",
                  val.status === "error" &&
                    "bg-red-400/10 border-red-400/30 text-red-300",
                  val.status === "not_configured" &&
                    "bg-subtle border-default text-muted-fg",
                )}
              >
                <div className="flex items-center gap-2">
                  <span>
                    {val.status === "ok" && "✅"}
                    {val.status === "error" && "❌"}
                    {val.status === "not_configured" && "⚪"}
                  </span>
                  <span className="font-medium capitalize">{key}</span>
                  {val.documents !== undefined && (
                    <span className="opacity-70">
                      {val.documents} documents
                    </span>
                  )}
                  {val.model && <span className="opacity-70">{val.model}</span>}
                </div>
                <div className="text-right">
                  {val.latency_ms && (
                    <span className="opacity-70">{val.latency_ms}ms</span>
                  )}
                  {val.error && (
                    <span className="max-w-[200px] truncate" title={val.error}>
                      {val.error}
                    </span>
                  )}
                  {val.status === "not_configured" && (
                    <span>Non configuré</span>
                  )}
                </div>
              </div>
            ),
          )}
        </div>
      )}
    </Section>
  );
}
