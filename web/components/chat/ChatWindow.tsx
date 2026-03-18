"use client";

import { useChat } from "ai/react";
import { useEffect, useRef } from "react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { Sparkles } from "lucide-react";

const STARTER_PROMPTS = [
  "Qui es-tu et que peux-tu faire pour moi ?",
  "Quels sont les horaires du secrétariat des étudiants ?",
  "Donne-moi un conseil pour réussir ma session d'examens.",
  "Peux-tu me faire un résumé du cours de 'Développement Web' ?",
];

interface Props {
  sessionId: string | null;
  onSessionCreated: (id: string) => void;
}

export function ChatWindow({ sessionId, onSessionCreated }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    setMessages,
    append,
  } = useChat({
    id: sessionId || "new_session",
    api: "/api/chat",
    body: { session_id: sessionId },
    onResponse: (res) => {
      // Récupère le session_id depuis le header si pas encore de session
      const newId = res.headers.get("X-Session-Id");
      if (newId && newId.length > 10 && !sessionId) onSessionCreated(newId);
    },
    onFinish: () => {
      // Recharge la liste des sessions après chaque réponse
      if (!sessionId) return;
    },
  });

  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    fetch(`/api/sessions/${sessionId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.messages) {
          setMessages(data.messages.map((m: any, i: number) => ({
            ...m,
            id: m.id || `loaded-${i}`,
          })));
        }
      })
      .catch(console.error); // Ajout d'une gestion d'erreur basique
  }, [sessionId, setMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full px-6 animate-fade-in">
            {/* ... En-tête ... */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
              {STARTER_PROMPTS.map((prompt, i) => (
                <button
                  key={prompt}
                  // CORRECTION : Utilisation de append() au lieu de tricher avec un événement DOM
                  onClick={() => append({ role: 'user', content: prompt })}
                  className="group flex items-start gap-2.5 px-4 py-3 rounded-lg text-left border border-default bg-surface hover:border-gold/30 hover:bg-gold-glow transition-all duration-150 animate-fade-up"
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <Sparkles size={13} className="mt-0.5 flex-shrink-0 text-gold opacity-60 group-hover:opacity-100 transition-opacity" />
                  <span className="text-sm text-muted-fg group-hover:text-main transition-colors leading-snug">
                    {prompt}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-2">
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
                <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mt-0.5 bg-gold-glow border border-gold/20">
                  <span className="text-gold text-xs">◈</span>
                </div>
                <div className="px-4 py-2.5 rounded-2xl rounded-tl-sm border border-default bg-surface text-sm text-muted-fg flex items-center gap-2">
                  <span className="text-xs">L'Oracle consulte les archives</span>
                  <span className="flex gap-1">
                    {[0,1,2].map(i => (
                      <span key={i} className="w-1 h-1 rounded-full bg-gold/60 animate-bounce" style={{animationDelay: `${i*150}ms`}} />
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
          <ChatInput value={input} onChange={handleInputChange} onSubmit={handleSubmit} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}