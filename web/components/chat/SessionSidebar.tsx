"use client";

import { useEffect, useState, useCallback } from "react";
import { MessageSquarePlus, Trash2, Clock } from "lucide-react";
import { clsx } from "clsx";

function FeedbackPanel({ sessionId }: { sessionId: string }) {
  const [hovered, setHovered] = useState(0);
  const [selected, setSelected] = useState(0);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Réinitialise si la session change
  useEffect(() => {
    setHovered(0);
    setSelected(0);
    setComment("");
    setSubmitted(false);
  }, [sessionId]);

  async function handleSubmit() {
    if (!selected) return;
    setSubmitting(true);
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          rating: selected,
          comment: comment.trim() || null,
        }),
      });
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="px-3 py-3 text-center text-xs text-muted-fg">
        Merci pour ton retour ✦
      </div>
    );
  }

  return (
    <div className="px-3 py-3 space-y-2">
      <p className="text-xs text-subtle-fg">Noter cette conversation</p>

      {/* Étoiles */}
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => setSelected(star)}
            className="text-lg leading-none transition-colors duration-100"
            aria-label={`Note ${star}`}
          >
            <span
              className={clsx(
                (hovered || selected) >= star
                  ? "text-gold"
                  : "text-muted-fg opacity-30",
              )}
            >
              ★
            </span>
          </button>
        ))}
      </div>

      {/* Commentaire + bouton */}
      {selected > 0 && (
        <div className="flex flex-col gap-1.5 animate-fade-up">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Un commentaire ? (optionnel)"
            rows={2}
            className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-default bg-surface-alt
                       text-main placeholder:text-subtle-fg focus:outline-none focus:border-gold/50
                       resize-none transition-colors duration-150"
          />
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="self-start px-3 py-1 text-xs rounded-lg bg-gold/10 border border-gold/30
                       text-gold hover:bg-gold/20 transition-colors duration-150 disabled:opacity-50"
          >
            {submitting ? "Envoi…" : "Envoyer"}
          </button>
        </div>
      )}
    </div>
  );
}

interface Session {
  session_id: string;
  title: string;
  updated_at: string;
  provider: string;
  model: string;
}

interface Props {
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "à l'instant";
  if (m < 60) return `il y a ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `il y a ${h}h`;
  const d = Math.floor(h / 24);
  return `il y a ${d}j`;
}

export function SessionSidebar({
  activeSessionId,
  onSelectSession,
  onNewSession,
}: Props) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  // Évite les erreurs d'hydratation côté serveur (Next.js)
  useEffect(() => {
    setMounted(true);
  }, []);

  // Fonction mémorisée pour éviter de la recréer à chaque rendu
  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) throw new Error("Erreur réseau");
      const data = await res.json();
      setSessions(data.sessions ?? []);
    } catch (e) {
      console.error(e);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // On charge les sessions uniquement au montage du composant
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const deleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Empêche le clic de sélectionner la session

    // Ajout d'une confirmation pour éviter les suppressions accidentelles
    if (
      !window.confirm("Êtes-vous sûr de vouloir supprimer cette conversation ?")
    ) {
      return;
    }

    await fetch(`/api/sessions/${id}`, { method: "DELETE" });
    setSessions((prev) => prev.filter((s) => s.session_id !== id));

    // Si la session supprimée était celle active, on en ouvre une nouvelle
    if (activeSessionId === id) {
      onNewSession();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-default">
        <button
          onClick={onNewSession}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md
                     text-sm font-medium text-gold border border-gold/30 bg-gold-glow
                     hover:bg-gold/10 transition-all duration-150"
        >
          <MessageSquarePlus size={14} />
          Nouvelle conversation
        </button>
      </div>

      {/* Liste */}
      <div className="flex-1 overflow-y-auto py-2 min-h-0">
        {loading && (
          <div className="px-4 py-8 text-center text-subtle-fg text-sm animate-pulse">
            Chargement…
          </div>
        )}

        {!loading && sessions.length === 0 && (
          <div className="px-4 py-8 text-center text-subtle-fg text-sm">
            Aucune conversation
          </div>
        )}

        {sessions.map((s, i) => (
          <div
            key={s.session_id}
            onClick={() => onSelectSession(s.session_id)}
            className={clsx(
              "group relative mx-2 mb-0.5 px-3 py-2.5 rounded-md cursor-pointer transition-all duration-150",
              "animate-fade-up",
              activeSessionId === s.session_id
                ? "bg-gold-glow border border-gold/20"
                : "hover:bg-subtle border border-transparent",
            )}
            style={{ animationDelay: `${i * 30}ms` }}
          >
            {/* Titre */}
            <p
              className={clsx(
                "text-sm truncate pr-6 leading-snug",
                activeSessionId === s.session_id
                  ? "text-main font-medium"
                  : "text-main",
              )}
            >
              {s.title || "Conversation sans titre"}
            </p>

            {/* Méta */}
            <div className="flex items-center gap-1.5 mt-0.5">
              <Clock size={10} className="text-subtle-fg" />
              {/* Utilisation de mounted pour l'hydratation de l'heure locale */}
              <span className="text-xs text-subtle-fg">
                {mounted ? timeAgo(s.updated_at) : "..."}
              </span>
              {s.provider && (
                <span className="text-xs text-subtle-fg opacity-60">
                  · {s.provider}
                </span>
              )}
            </div>

            {/* Supprimer */}
            <button
              onClick={(e) => deleteSession(e, s.session_id)}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded opacity-0
                         group-hover:opacity-100 text-subtle-fg hover:text-red-400
                         transition-all duration-150"
              aria-label="Supprimer"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </div>

      {/* Feedback — affiché uniquement quand une session est active */}
      {activeSessionId && (
        <div className="border-t border-default">
          <FeedbackPanel sessionId={activeSessionId} />
        </div>
      )}
    </div>
  );
}
