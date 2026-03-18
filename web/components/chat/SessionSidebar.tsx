"use client";

import { useEffect, useState, useCallback } from "react";
import { MessageSquarePlus, Trash2, Clock } from "lucide-react";
import { clsx } from "clsx";

interface Session {
  session_id: string;
  title:      string;
  updated_at: string;
  provider:   string;
  model:      string;
}

interface Props {
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession:    () => void;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)   return "à l'instant";
  if (m < 60)  return `il y a ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `il y a ${h}h`;
  const d = Math.floor(h / 24);
  return `il y a ${d}j`;
}

export function SessionSidebar({ activeSessionId, onSelectSession, onNewSession }: Props) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading]   = useState(true);
  const [mounted, setMounted]   = useState(false);

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
    if (!window.confirm("Êtes-vous sûr de vouloir supprimer cette conversation ?")) {
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
      <div className="flex-1 overflow-y-auto py-2">
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
                : "hover:bg-subtle border border-transparent"
            )}
            style={{ animationDelay: `${i * 30}ms` }}
          >
            {/* Titre */}
            <p className={clsx(
              "text-sm truncate pr-6 leading-snug",
              activeSessionId === s.session_id ? "text-main font-medium" : "text-main"
            )}>
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
                <span className="text-xs text-subtle-fg opacity-60">· {s.provider}</span>
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
    </div>
  );
}