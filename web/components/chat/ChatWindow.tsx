"use client";

import { useChat } from "ai/react";
import { useEffect, useRef, useState } from "react";
import React from "react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { CotDrawer } from "./CotDrawer";
import { Sparkles, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface CotResult {
  source: string;
  content: string;
  rrf_score: number;
  confidence: "high" | "medium" | "low";
}

const STARTER_PROMPTS = [
  "Je suis tout nouveau sur Dofus. Par où commencer et quelle classe choisir ?",
  "Explique-moi les mécaniques de combat : PA, PM, portée, défis de combat.",
  "Comment fonctionne un donjon ? Comment se préparer et quoi apporter ?",
  "Quelles sont les meilleures façons de gagner des kamas quand on débute ?",
];

interface Props {
  sessionId: string | null;
  onSessionCreated: (id: string) => void;
}

export function ChatWindow({ sessionId, onSessionCreated }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [cotOpen, setCotOpen] = useState(false);
  const [cotResults, setCotResults] = useState<CotResult[]>([]);

  // Lit la config depuis localStorage (sauvegardée depuis l'admin)
  const getOracleConfig = () => {
    if (typeof window === "undefined") return {};
    return {
      provider: localStorage.getItem("oracle_provider") || "groq",
      model: localStorage.getItem("oracle_model") || "llama-3.3-70b-versatile",
      temperature: parseFloat(
        localStorage.getItem("oracle_temperature") || "0",
      ),
      k_final: parseInt(localStorage.getItem("oracle_k_final") || "5"),
    };
  };

  const currentSessionRef = React.useRef<string | null>(sessionId);
  useEffect(() => {
    currentSessionRef.current = sessionId;
  }, [sessionId]);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    setMessages,
    append,
    data,
  } = useChat({
    id: sessionId || "new_session",
    api: "/api/chat",
    body: { session_id: sessionId, ...getOracleConfig() },
    onResponse: (res) => {
      const newId = res.headers.get("X-Session-Id");
      if (newId && newId.length > 10 && !currentSessionRef.current) {
        currentSessionRef.current = newId;
        onSessionCreated(newId);
      }
    },
  });

  // Extrait le dernier CoT depuis les annotations AI SDK
  useEffect(() => {
    if (!data?.length) return;
    const last = [...data].reverse().find((d: any) => d?.cotResults);
    if (last) setCotResults((last as any).cotResults);
  }, [data]);

  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    fetch(`/api/sessions/${sessionId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.messages) {
          setMessages(
            data.messages.map((m: any, i: number) => ({
              ...m,
              id: m.id || `loaded-${i}`,
            })),
          );
        }
      })
      .catch((err) => console.error("Erreur chargement session:", err));
  }, [sessionId, setMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isEmpty = messages.length === 0;

  const cotButton =
    cotResults.length > 0 ? (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-[var(--gold)] hover:bg-[var(--gold-glow)]"
                onClick={() => setCotOpen(true)}
              />
            }
          >
            <BookOpen size={13} />
          </TooltipTrigger>
          <TooltipContent side="top">
            <p className="text-xs">
              {cotResults.length} source{cotResults.length > 1 ? "s" : ""}{" "}
              consultée{cotResults.length > 1 ? "s" : ""}
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    ) : null;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full px-6 py-8 animate-fade-in">
            {/* Oracle header */}
            <div className="text-center mb-8 space-y-3">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[var(--gold-glow)] border border-[var(--gold)]/20">
                <span className="text-[var(--gold)] text-3xl">◈</span>
              </div>
              <div>
                <h2 className="font-cinzel text-lg font-semibold text-[var(--text)] tracking-widest uppercase">
                  L'Oracle
                </h2>
                <p className="text-sm text-[var(--text-muted)] mt-1">
                  Pose ta question sur Dofus, je consulte les archives
                </p>
              </div>
            </div>

            {/* Starter prompts */}
            <div className="hidden md:grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
              {STARTER_PROMPTS.map((prompt, i) => (
                <button
                  key={prompt}
                  onClick={() => append({ role: "user", content: prompt })}
                  className="group flex items-start gap-3 px-4 py-3.5 rounded-xl text-left border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--gold)]/30 hover:bg-[var(--gold-glow)] transition-all duration-150 animate-fade-up"
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <Sparkles
                    size={14}
                    className="mt-0.5 flex-shrink-0 text-[var(--gold)] opacity-50 group-hover:opacity-100 transition-opacity"
                  />
                  <span className="text-sm text-[var(--text-muted)] group-hover:text-[var(--text)] transition-colors leading-snug">
                    {prompt}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-3">
            {messages.map((msg, i) => (
              <ChatMessage
                key={msg.id || i}
                role={msg.role as "user" | "assistant"}
                content={msg.content}
                index={i}
                isLast={i === messages.length - 1}
                isLoading={isLoading && i === messages.length - 1}
              />
            ))}
            {/* Indicateur "L'Oracle réfléchit" */}
            {isLoading && messages[messages.length - 1]?.role === "user" && (
              <div className="flex gap-3 animate-fade-up">
                <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mt-0.5 bg-[var(--gold-glow)] border border-[var(--gold)]/20">
                  <span className="text-[var(--gold)] text-xs">◈</span>
                </div>
                <div className="px-4 py-3 rounded-2xl rounded-tl-sm border border-[var(--border)] bg-[var(--surface)] text-sm text-[var(--text-muted)] flex items-center gap-3">
                  <span className="text-xs">
                    L'Oracle consulte les archives
                  </span>
                  <span className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={`dot-${i}`}
                        className="w-1.5 h-1.5 rounded-full bg-[var(--gold)]/50 animate-bounce"
                        style={{ animationDelay: `${i * 150}ms` }}
                      />
                    ))}
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="border-t border-default bg-surface/50 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 py-3">
          <ChatInput
            value={input}
            onChange={handleInputChange}
            onSubmit={handleSubmit}
            isLoading={isLoading}
          >
            {cotButton}
          </ChatInput>
        </div>
      </div>

      <CotDrawer
        open={cotOpen}
        onClose={() => setCotOpen(false)}
        results={cotResults}
      />
    </div>
  );
}
