"use client";

import { useEffect, useState, useCallback } from "react";
import { MessageSquarePlus, Trash2, Clock, Star, Settings, ChevronDown, ChevronUp, Cpu, Thermometer, Send, CheckCircle2 } from "lucide-react";
import { clsx } from "clsx";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

// ── Feedback ─────────────────────────────────────────────────────────────────

function FeedbackPanel({ sessionId }: { sessionId: string }) {
  const [hovered, setHovered]   = useState(0);
  const [selected, setSelected] = useState(0);
  const [comment, setComment]   = useState("");
  const [submitted, setSubmitted]   = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setHovered(0); setSelected(0); setComment(""); setSubmitted(false);
  }, [sessionId]);

  async function handleSubmit() {
    if (!selected) return;
    setSubmitting(true);
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, rating: selected, comment: comment.trim() || null }),
      });
      setSubmitted(true);
    } finally { setSubmitting(false); }
  }

  if (submitted) {
    return (
      <div className="px-4 py-4 flex flex-col items-center gap-2 text-center animate-fade-up">
        <CheckCircle2 size={20} className="text-emerald-400" />
        <p className="text-xs text-[var(--text-muted)]">Merci pour ton retour !</p>
      </div>
    );
  }

  return (
    <div className="px-4 py-4 space-y-3">
      <p className="text-[10px] text-[var(--text-subtle)] uppercase tracking-wider">Évaluer cette conversation</p>

      {/* Stars */}
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => setSelected(star)}
            className="transition-transform hover:scale-110 duration-100"
            aria-label={`Note ${star}`}
          >
            <Star
              size={18}
              className="transition-colors duration-100"
              fill={(hovered || selected) >= star ? "var(--gold)" : "transparent"}
              stroke={(hovered || selected) >= star ? "var(--gold)" : "var(--text-subtle)"}
            />
          </button>
        ))}
        {selected > 0 && (
          <span className="ml-2 text-xs text-[var(--gold)]">
            {["", "Mauvais", "Passable", "Correct", "Bien", "Excellent"][selected]}
          </span>
        )}
      </div>

      {/* Comment + submit */}
      {selected > 0 && (
        <div className="space-y-2 animate-fade-up">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Commentaire optionnel…"
            rows={2}
            className="w-full px-2.5 py-2 text-xs rounded-lg border border-[var(--border)] bg-[var(--bg-subtle)]
                       text-[var(--text)] placeholder:text-[var(--text-subtle)] focus:outline-none
                       focus:border-[var(--gold)]/50 resize-none transition-colors"
          />
          <Button
            onClick={handleSubmit}
            disabled={submitting}
            size="sm"
            className="w-full h-7 text-xs bg-[var(--gold)]/10 hover:bg-[var(--gold)]/20 text-[var(--gold)] border border-[var(--gold)]/30 hover:border-[var(--gold)]/50"
          >
            {submitting ? "Envoi…" : <><Send size={11} className="mr-1" /> Envoyer</>}
          </Button>
        </div>
      )}
    </div>
  );
}

// ── User preferences (model info) ────────────────────────────────────────────

function UserPrefsPanel() {
  const [open, setOpen] = useState(false);
  const [provider, setProvider]   = useState("");
  const [model, setModel]         = useState("");
  const [temperature, setTemperature] = useState("");
  const [kFinal, setKFinal]       = useState("");

  useEffect(() => {
    setProvider(localStorage.getItem("oracle_provider") || "groq");
    setModel(localStorage.getItem("oracle_model") || "llama-3.3-70b-versatile");
    setTemperature(localStorage.getItem("oracle_temperature") || "0");
    setKFinal(localStorage.getItem("oracle_k_final") || "5");
  }, []);

  return (
    <div className="border-t border-[var(--border)]">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-xs text-[var(--text-subtle)] hover:text-[var(--text)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <Settings size={12} />
          <span>Paramètres actifs</span>
        </div>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {open && (
        <div className="px-4 pb-3 space-y-2 animate-fade-up">
          <div className="grid grid-cols-2 gap-1.5">
            <div className="bg-[var(--bg-subtle)] rounded-md px-2.5 py-2 space-y-0.5">
              <div className="flex items-center gap-1 text-[9px] text-[var(--text-subtle)] uppercase tracking-wider">
                <Cpu size={9} /> Provider
              </div>
              <p className="text-xs font-medium text-[var(--text)] capitalize">{provider}</p>
            </div>
            <div className="bg-[var(--bg-subtle)] rounded-md px-2.5 py-2 space-y-0.5">
              <div className="flex items-center gap-1 text-[9px] text-[var(--text-subtle)] uppercase tracking-wider">
                <Thermometer size={9} /> Temp.
              </div>
              <p className="text-xs font-medium text-[var(--text)]">{temperature}</p>
            </div>
          </div>
          <div className="bg-[var(--bg-subtle)] rounded-md px-2.5 py-2 space-y-0.5">
            <p className="text-[9px] text-[var(--text-subtle)] uppercase tracking-wider">Modèle</p>
            <p className="text-[11px] font-medium text-[var(--text)] truncate">{model}</p>
          </div>
          <div className="bg-[var(--bg-subtle)] rounded-md px-2.5 py-2 space-y-0.5">
            <p className="text-[9px] text-[var(--text-subtle)] uppercase tracking-wider">Sources RAG (k)</p>
            <p className="text-xs font-medium text-[var(--text)]">{kFinal} chunks</p>
          </div>
          <p className="text-[10px] text-[var(--text-subtle)] text-center">
            Modifiable dans <span className="text-[var(--gold)]">Administration</span>
          </p>
        </div>
      )}
    </div>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────

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
  if (m < 60) return `il y a ${m}min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `il y a ${h}h`;
  return `il y a ${Math.floor(h / 24)}j`;
}

// ── Main component ────────────────────────────────────────────────────────────

export function SessionSidebar({ activeSessionId, onSelectSession, onNewSession }: Props) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading]   = useState(true);
  const [mounted, setMounted]   = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) throw new Error();
      const data = await res.json();
      setSessions(data.sessions ?? []);
    } catch { setSessions([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);

  const deleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm("Supprimer cette conversation ?")) return;
    await fetch(`/api/sessions/${id}`, { method: "DELETE" });
    setSessions((prev) => prev.filter((s) => s.session_id !== id));
    if (activeSessionId === id) onNewSession();
  };

  return (
    <div className="flex flex-col h-full bg-[var(--surface)]">
      {/* Header */}
      <div className="p-3 border-b border-[var(--border)]">
        <Button
          onClick={onNewSession}
          className="w-full bg-[var(--gold-glow)] hover:bg-[var(--gold)]/15 text-[var(--gold)] border border-[var(--gold)]/30 hover:border-[var(--gold)]/50 font-medium text-sm gap-2"
          variant="outline"
        >
          <MessageSquarePlus size={14} />
          Nouvelle conversation
        </Button>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto py-2 min-h-0">
        {loading && (
          <div className="px-4 py-8 text-center">
            <div className="flex justify-center gap-1">
              {[0, 1, 2].map(i => (
                <div key={i} className="w-1.5 h-1.5 rounded-full bg-[var(--border)] animate-bounce"
                  style={{ animationDelay: `${i * 150}ms` }} />
              ))}
            </div>
          </div>
        )}

        {!loading && sessions.length === 0 && (
          <div className="px-4 py-10 text-center space-y-2">
            <MessageSquarePlus size={24} className="mx-auto text-[var(--text-subtle)] opacity-40" />
            <p className="text-xs text-[var(--text-subtle)]">Aucune conversation</p>
          </div>
        )}

        <div className="space-y-0.5 px-2">
          {sessions.map((s, i) => (
            <div
              key={s.session_id}
              onClick={() => onSelectSession(s.session_id)}
              className={clsx(
                "group relative px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150 animate-fade-up",
                activeSessionId === s.session_id
                  ? "bg-[var(--gold-glow)] border border-[var(--gold)]/20"
                  : "hover:bg-[var(--bg-subtle)] border border-transparent",
              )}
              style={{ animationDelay: `${i * 30}ms` }}
            >
              {/* Title */}
              <p className={clsx(
                "text-[13px] truncate pr-6 leading-snug",
                activeSessionId === s.session_id ? "text-[var(--text)] font-medium" : "text-[var(--text)]",
              )}>
                {s.title || "Conversation sans titre"}
              </p>

              {/* Meta */}
              <div className="flex items-center gap-1.5 mt-1">
                <Clock size={9} className="text-[var(--text-subtle)]" />
                <span className="text-[10px] text-[var(--text-subtle)]">
                  {mounted ? timeAgo(s.updated_at) : "…"}
                </span>
                {s.provider && (
                  <Badge variant="outline" className="text-[9px] h-4 px-1 border-[var(--border)] text-[var(--text-subtle)] ml-auto">
                    {s.provider}
                  </Badge>
                )}
              </div>

              {/* Delete */}
              <button
                onClick={(e) => deleteSession(e, s.session_id)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded opacity-0
                           group-hover:opacity-100 text-[var(--text-subtle)] hover:text-red-400
                           transition-all duration-150"
                aria-label="Supprimer"
              >
                <Trash2 size={11} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Feedback */}
      {activeSessionId && (
        <>
          <Separator className="bg-[var(--border)]" />
          <FeedbackPanel sessionId={activeSessionId} />
        </>
      )}

      {/* User prefs */}
      <UserPrefsPanel />
    </div>
  );
}
