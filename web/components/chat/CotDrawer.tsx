"use client";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

interface CotResult {
  source: string;
  content: string;
  rrf_score: number;
  confidence: "high" | "medium" | "low";
}

interface Props {
  open: boolean;
  onClose: () => void;
  results: CotResult[];
}

const CONFIDENCE_CONFIG = {
  high: {
    label: "Haute",
    className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  },
  medium: {
    label: "Moyenne",
    className: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  },
  low: {
    label: "Faible",
    className: "bg-red-500/15 text-red-400 border-red-500/20",
  },
};

export function CotDrawer({ open, onClose, results }: Props) {
  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent
        side="right"
        className="w-[420px] bg-[var(--surface)] border-l border-[var(--border)] p-0"
      >
        <SheetHeader className="px-5 pt-5 pb-3">
          <SheetTitle className="font-cinzel text-[var(--gold)] text-sm tracking-widest uppercase">
            Archives consultées
          </SheetTitle>
          <p className="text-xs text-[var(--text-subtle)]">
            {results.length} source{results.length > 1 ? "s" : ""} — recherche
            hybride (cosine + BM25 + RRF)
          </p>
        </SheetHeader>

        <Separator className="bg-[var(--border)]" />

        <ScrollArea className="h-[calc(100vh-100px)] px-5 py-4">
          <div className="space-y-4">
            {results.map((r, i) => {
              const conf = CONFIDENCE_CONFIG[r.confidence];
              return (
                <div
                  key={i}
                  className="rounded-lg border border-[var(--border)] bg-[var(--bg-subtle)] p-3 space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-[var(--text)] truncate max-w-[260px]">
                      {r.source}
                    </span>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <Badge
                        variant="outline"
                        className={`text-[10px] px-1.5 py-0 h-4 ${conf.className}`}
                      >
                        {conf.label}
                      </Badge>
                      <span className="text-[10px] text-[var(--text-subtle)] font-mono">
                        {r.rrf_score.toFixed(4)}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-[var(--text-muted)] leading-relaxed line-clamp-4">
                    {r.content}
                  </p>
                </div>
              );
            })}

            {results.length === 0 && (
              <p className="text-xs text-[var(--text-subtle)] text-center py-8">
                Aucune source consultée pour cette réponse.
              </p>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
