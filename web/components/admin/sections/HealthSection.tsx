"use client";

import {
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Search,
  Activity,
} from "lucide-react";
import { clsx } from "clsx";
import { Section } from "./shared";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface Props {
  healthData: any;
  healthState: "idle" | "running" | "done";
  onCheck: () => void;
}

export function HealthSection({ healthData, healthState, onCheck }: Props) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[var(--text)]">
          Santé du Système
        </h2>
        <Button
          onClick={onCheck}
          disabled={healthState === "running"}
          size="sm"
          className="bg-[var(--gold)] hover:bg-[var(--gold-light)] text-[#0a0c10] font-medium"
        >
          {healthState === "running" ? (
            <>
              <Loader2 size={14} className="mr-2 animate-spin" />
              Analyse...
            </>
          ) : (
            <>
              <Search size={14} className="mr-2" />
              Lancer un diagnostic
            </>
          )}
        </Button>
      </div>

      {!healthData && healthState === "idle" && (
        <Card className="border-dashed border-[var(--border)] bg-transparent">
          <CardContent className="py-10 text-center">
            <Activity className="w-8 h-8 mx-auto text-[var(--text-subtle)] mb-3 opacity-20" />
            <p className="text-sm text-[var(--text-muted)]">
              Aucun diagnostic récent. Cliquez sur le bouton pour vérifier les
              services.
            </p>
          </CardContent>
        </Card>
      )}

      {healthData && (
        <div className="grid grid-cols-1 gap-3">
          {Object.entries(healthData.checks || {}).map(
            ([key, val]: [string, any]) => (
              <div
                key={key}
                className={clsx(
                  "flex items-center justify-between p-4 rounded-xl border transition-all",
                  val.status === "ok" &&
                    "bg-emerald-500/5 border-emerald-500/20 text-emerald-400",
                  val.status === "error" &&
                    "bg-red-500/5 border-red-500/20 text-red-400",
                  val.status === "not_configured" &&
                    "bg-[var(--bg-subtle)] border-[var(--border)] text-[var(--text-subtle)]",
                )}
              >
                <div className="flex items-center gap-4">
                  <div
                    className={clsx(
                      "p-2 rounded-lg",
                      val.status === "ok" && "bg-emerald-500/10",
                      val.status === "error" && "bg-red-500/10",
                      val.status === "not_configured" &&
                        "bg-[var(--border)]/50",
                    )}
                  >
                    {val.status === "ok" && <CheckCircle2 size={18} />}
                    {val.status === "error" && <XCircle size={18} />}
                    {val.status === "not_configured" && (
                      <AlertCircle size={18} />
                    )}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold capitalize text-[var(--text)]">
                      {key}
                    </h3>
                    <div className="flex items-center gap-3 mt-0.5">
                      {val.documents !== undefined && (
                        <span className="text-[10px] opacity-70 uppercase tracking-wider font-medium">
                          {val.documents} archives
                        </span>
                      )}
                      {val.model && (
                        <span className="text-[10px] opacity-70 uppercase tracking-wider font-medium">
                          {val.model}
                        </span>
                      )}
                      {val.status === "not_configured" && (
                        <span className="text-[10px] uppercase tracking-wider">
                          Non configuré
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  {val.latency_ms && (
                    <div className="flex items-center gap-1.5 justify-end">
                      <span className="text-xs font-mono font-medium">
                        {val.latency_ms}ms
                      </span>
                      <div className="w-1 h-1 rounded-full bg-current opacity-40" />
                    </div>
                  )}
                  {val.error && (
                    <span
                      className="text-[10px] font-medium opacity-80 bg-red-500/10 px-2 py-0.5 rounded"
                      title={val.error}
                    >
                      Erreur critique
                    </span>
                  )}
                </div>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}
