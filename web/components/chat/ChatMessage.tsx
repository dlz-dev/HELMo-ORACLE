"use client";

import { useState } from "react";
import { clsx } from "clsx";
import { SourceViewer } from "./SourceViewer";
import { User, Sparkles, Copy, Check } from "lucide-react";
import { Streamdown } from "streamdown";
import "streamdown/styles.css";
import { Badge } from "@/components/ui/badge";
import {
  Sources,
  SourcesTrigger,
  SourcesContent,
} from "../ai-elements/sources";
import {
  ChainOfThought,
  ChainOfThoughtHeader,
  ChainOfThoughtContent,
  ChainOfThoughtStep,
} from "../ai-elements/chain-of-thought";
import {
  ScanSearch,
  Layers,
  Database,
  ArrowUpDown,
  PenLine,
} from "lucide-react";

interface CotResult {
  source: string;
  content: string;
  rrf_score: number;
  confidence: "high" | "medium" | "low";
}

const PIPELINE_STEP_CONFIG = [
  { id: "analyse", label: "Analyse de la question", Icon: ScanSearch },
  { id: "embedding", label: "Génération de l'embedding", Icon: Layers },
  { id: "retrieval", label: "Recherche dans les archives", Icon: Database },
  { id: "reranking", label: "Reranking des résultats", Icon: ArrowUpDown },
  { id: "answer", label: "Rédaction de la réponse", Icon: PenLine },
];

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

interface Props {
  role: "user" | "assistant";
  content: string;
  index: number;
  isLast: boolean;
  isLoading: boolean;
  cotResults?: CotResult[];
  pipelineSteps?: string[];
  currentPipelineStep?: string | null;
}

export function ChatMessage({
  role,
  content,
  index,
  isLast,
  isLoading,
  cotResults,
  pipelineSteps,
  currentPipelineStep,
}: Props) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);
  const [viewer, setViewer] = useState<{
    filename: string;
    passage: string;
  } | null>(null);

  const VIEWABLE_EXTENSIONS = [".txt", ".md", ".csv", ".json", ".pdf"];

  function handleCopy() {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const showSteps = !isUser && pipelineSteps && pipelineSteps.length > 0;

  return (
    <>
      <div
        className={clsx(
          "group flex gap-3 animate-fade-up",
          isUser ? "flex-row-reverse" : "flex-row",
        )}
        style={{ animationDelay: `${Math.min(index * 20, 200)}ms` }}
      >
        {/* Avatar */}
        <div
          className={clsx(
            "flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mt-0.5",
            isUser
              ? "bg-[var(--bg-subtle)] border border-[var(--border)]"
              : "bg-[var(--gold-glow)] border border-[var(--gold)]/20",
          )}
        >
          {isUser ? (
            <User size={13} className="text-[var(--text-muted)]" />
          ) : (
            <Sparkles size={13} className="text-[var(--gold)]" />
          )}
        </div>

        {/* Bubble + actions */}
        <div
          className={clsx(
            "flex flex-col gap-1",
            isUser ? "items-end" : "items-start",
            "max-w-[75%]",
          )}
        >
          <div
            className={clsx(
              "px-4 py-3 rounded-2xl text-sm leading-relaxed",
              isUser
                ? "bg-[var(--bg-subtle)] text-[var(--text)] rounded-tr-sm border border-[var(--border)]"
                : "bg-[var(--surface)] text-[var(--text)] rounded-tl-sm border border-[var(--border)] shadow-[var(--shadow-sm)]",
            )}
          >
            {/* Points de chargement si vide, sinon texte */}
            {isLoading && isLast && !content ? (
              <div className="flex items-center gap-1.5 h-5">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-[var(--gold)]/60 animate-bounce"
                    style={{ animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </div>
            ) : content ? (
              <div
                className="prose prose-sm dark:prose-invert max-w-none
              prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-headings:my-2
              prose-strong:text-[var(--text)] prose-code:text-[var(--gold)]
              prose-code:bg-[var(--bg-subtle)] prose-code:px-1.5 prose-code:rounded
              prose-code:text-xs prose-code:before:content-none prose-code:after:content-none"
              >
                <Streamdown
                  animated
                  isAnimating={isLoading && isLast}
                  caret="circle"
                >
                  {content}
                </Streamdown>
              </div>
            ) : null}
          </div>

          {/* Étapes stables sous la bulle */}
          {showSteps && (
            <div className="mt-1 px-1 w-full">
              <ChainOfThought>
                <ChainOfThoughtHeader className="text-xs text-[var(--text-subtle)] hover:text-[var(--text-muted)]">
                  {isLoading && !content
                    ? "Oracle en réflexion..."
                    : `${pipelineSteps.length} étape${pipelineSteps.length > 1 ? "s" : ""} exécutée${pipelineSteps.length > 1 ? "s" : ""}`}
                </ChainOfThoughtHeader>
                <ChainOfThoughtContent>
                  {PIPELINE_STEP_CONFIG.map((s, i) => {
                    const currentIdx = PIPELINE_STEP_CONFIG.findIndex(
                      (step) => step.id === currentPipelineStep,
                    );
                    let status: "complete" | "active" | "pending" = "pending";

                    if (pipelineSteps.includes(s.id)) {
                      status = "complete";
                    } else if (s.id === currentPipelineStep) {
                      status = "active";
                    } else if (currentIdx !== -1 && i < currentIdx) {
                      status = "complete";
                    }

                    return (
                      <ChainOfThoughtStep
                        key={s.id}
                        icon={s.Icon}
                        label={s.label}
                        status={status}
                      />
                    );
                  })}
                </ChainOfThoughtContent>
              </ChainOfThought>
            </div>
          )}

          {/* Sources — assistant only, après la réponse */}
          {!isUser && !isLoading && cotResults && cotResults.length > 0 && (
            <div className="mt-1 px-1 w-full max-w-full">
              <Sources>
                <SourcesTrigger count={cotResults.length} />
                <SourcesContent>
                  {cotResults.map((r, i) => {
                    const conf = CONFIDENCE_CONFIG[r.confidence];
                    return (
                      <div
                        key={i}
                        className="rounded-lg border border-[var(--border)] bg-[var(--bg-subtle)] p-2.5 space-y-1.5 overflow-hidden"
                      >
                        <div className="flex items-center justify-between gap-2 min-w-0">
                          <span className="text-[11px] font-medium text-[var(--text)] truncate min-w-0">
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
                        <p className="text-[11px] text-[var(--text-muted)] leading-relaxed line-clamp-3 break-all overflow-hidden w-full">
                          {r.content}
                        </p>
                        {VIEWABLE_EXTENSIONS.includes(
                          r.source
                            .slice(r.source.lastIndexOf("."))
                            .toLowerCase(),
                        ) && (
                          <button
                            onClick={() =>
                              setViewer({
                                filename: r.source,
                                passage: r.content,
                              })
                            }
                            className="text-[10px] text-[var(--gold)] hover:underline"
                          >
                            Voir dans le document →
                          </button>
                        )}
                      </div>
                    );
                  })}
                </SourcesContent>
              </Sources>
            </div>
          )}

          {/* Copy button — assistant only, visible on hover */}
          {!isUser && content && !isLoading && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-[var(--text-subtle)]
                       opacity-0 group-hover:opacity-100 hover:text-[var(--text)] hover:bg-[var(--bg-subtle)]
                       transition-all duration-150"
            >
              {copied ? (
                <>
                  <Check size={10} className="text-emerald-400" /> Copié
                </>
              ) : (
                <>
                  <Copy size={10} /> Copier
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {viewer && (
        <SourceViewer
          filename={viewer.filename}
          passage={viewer.passage}
          onClose={() => setViewer(null)}
        />
      )}
    </>
  );
}
