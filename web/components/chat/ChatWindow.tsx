"use client";

import { useChat } from "ai/react";
import { useEffect, useRef, useState } from "react";
import React from "react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { CotDrawer } from "./CotDrawer";
import { ChevronRight, BookOpen } from "lucide-react";
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
  isGuest?: boolean;
  firstName?: string;
}

export function ChatWindow({
  sessionId,
  onSessionCreated,
  isGuest = false,
  firstName = "",
}: Props) {
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

  const [limitReached, setLimitReached] = useState(false);

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
    onError: (err) => {
      if (err.message.includes("429")) setLimitReached(true);
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
          <div className="relative flex flex-col items-center justify-center h-full px-6 py-8 overflow-hidden animate-fade-in">
            {/* Gradient background */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background:
                  "radial-gradient(ellipse 80% 60% at 50% 10%, rgba(201,168,76,0.18) 0%, rgba(201,168,76,0.05) 45%, transparent 70%)",
              }}
            />

            {/* Orb */}
            <div
              className="relative mb-10 orb-float animate-fade-up"
              style={{ width: 200, height: 200, animationDelay: "0ms" }}
            >
              {/* Ambient halo — large soft glow behind everything */}
              <div
                className="absolute rounded-full orb-pulse"
                style={{
                  inset: "-55%",
                  background:
                    "radial-gradient(circle, rgba(201,168,76,0.28) 0%, rgba(201,168,76,0.06) 50%, transparent 70%)",
                  filter: "blur(24px)",
                  pointerEvents: "none",
                }}
              />

              {/* Ring 1 — gold */}
              <div
                className="absolute rounded-full orb-ring-1"
                style={{
                  inset: 0,
                  border: "1px solid rgba(201,168,76,0.35)",
                }}
              />
              {/* Ring 2 — subtler gold, reverse */}
              <div
                className="absolute rounded-full orb-ring-2"
                style={{
                  inset: 20,
                  border: "1px solid rgba(201,168,76,0.18)",
                }}
              />

              {/* Core sphere */}
              <div
                className="absolute rounded-full"
                style={{
                  inset: 30,
                  background:
                    "radial-gradient(circle at 33% 28%, rgba(255,248,180,0.92) 0%, rgba(225,180,55,0.75) 18%, rgba(201,168,76,0.5) 42%, rgba(160,110,20,0.2) 68%, transparent 100%)",
                  boxShadow:
                    "0 0 45px rgba(201,168,76,0.6), 0 0 90px rgba(201,168,76,0.28), 0 0 150px rgba(201,168,76,0.1)",
                  border: "1px solid rgba(201,168,76,0.3)",
                }}
              >
                {/* Specular highlight */}
                <div
                  style={{
                    position: "absolute",
                    top: "14%",
                    left: "16%",
                    width: "30%",
                    height: "20%",
                    borderRadius: "50%",
                    background:
                      "radial-gradient(ellipse, rgba(255,255,255,0.7) 0%, transparent 100%)",
                    filter: "blur(4px)",
                  }}
                />
              </div>
            </div>

            {/* Title + description */}
            <div className="relative text-center mb-8 space-y-2 animate-fade-up" style={{ animationDelay: "60ms" }}>
              <h2 className="font-cinzel text-3xl font-semibold text-[var(--text)] tracking-wide">
                Bonjour{firstName ? ` ${firstName}` : ""}&nbsp;!
              </h2>
              <p className="text-sm text-[var(--text-muted)]">
                Pose ta question sur Dofus, je consulte les archives
              </p>
            </div>

            {/* Floating input */}
            <div
              className="relative w-full max-w-2xl animate-fade-up"
              style={{
                animationDelay: "120ms",
                filter: "drop-shadow(0 8px 32px rgba(201,168,76,0.12)) drop-shadow(0 2px 8px rgba(0,0,0,0.12))",
              }}
            >
              <ChatInput
                value={input}
                onChange={handleInputChange}
                onSubmit={handleSubmit}
                isLoading={isLoading}
              />
            </div>

            {/* Suggestions */}
            <div className="relative w-full max-w-2xl mt-4 animate-fade-up" style={{ animationDelay: "180ms", paddingLeft: "12px", paddingRight: "12px" }}>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-subtle)] mb-2 px-1">
                Suggestions
              </p>
              <ul className="space-y-0.5">
                {STARTER_PROMPTS.map((prompt) => (
                  <li key={prompt}>
                    <button
                      onClick={() => append({ role: "user", content: prompt })}
                      className="group w-full text-left flex items-center gap-2 px-2 py-1.5 rounded-lg
                                 text-sm text-[var(--text-muted)] hover:text-[var(--text)]
                                 hover:bg-[var(--gold-glow)] transition-all duration-150"
                    >
                      <ChevronRight
                        size={12}
                        className="flex-shrink-0 text-[var(--gold)] opacity-40 group-hover:opacity-100 transition-opacity"
                      />
                      {prompt}
                    </button>
                  </li>
                ))}
              </ul>
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
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    className="text-[var(--gold)] flex-shrink-0"
                  >
                    <path
                      fill="currentColor"
                      d="M12 1A11 11 0 1 0 23 12 11 11 0 0 0 12 1Zm0 19a8 8 0 1 1 8-8 8 8 0 0 1-8 8Z"
                      opacity=".25"
                    />
                    <path
                      fill="currentColor"
                      d="M12 4a8 8 0 0 1 7.89 6.7A1.53 1.53 0 0 0 21.38 12h0a1.5 1.5 0 0 0 1.48-1.75 11 11 0 0 0-21.72 0A1.5 1.5 0 0 0 2.62 12h0a1.53 1.53 0 0 0 1.49-1.3A8 8 0 0 1 12 4Z"
                    >
                      <animateTransform
                        attributeName="transform"
                        dur="0.75s"
                        repeatCount="indefinite"
                        type="rotate"
                        values="0 12 12;360 12 12"
                      />
                    </path>
                  </svg>
                  <span className="text-xs">
                    L'Oracle consulte les archives
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {(limitReached ||
        (isGuest && messages.filter((m) => m.role === "user").length >= 5)) && (
        <div className="text-center text-sm py-2 px-4 bg-[var(--gold-glow)] border-t border-[var(--gold)]/20 text-[var(--gold)]">
          Limite de 5 messages atteinte. Connectez-vous pour continuer.
        </div>
      )}

      {!isEmpty && (
        <div className="border-t border-default bg-surface/50 backdrop-blur-sm">
          <div className="max-w-3xl mx-auto px-4 py-3">
            <ChatInput
              value={input}
              onChange={handleInputChange}
              onSubmit={handleSubmit}
              isLoading={
                isLoading ||
                (isGuest && messages.filter((m) => m.role === "user").length >= 5)
              }
            >
              {cotButton}
            </ChatInput>
          </div>
        </div>
      )}

      <CotDrawer
        open={cotOpen}
        onClose={() => setCotOpen(false)}
        results={cotResults}
      />
    </div>
  );
}
