"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  MessageSquarePlus,
  Trash2,
  Clock,
  Star,
  Cpu,
  Thermometer,
  Send,
  CheckCircle2,
  MessageSquare,
  BookOpen,
  HelpCircle,
  Shield,
  Sun,
  Moon,
  LogOut,
  Settings,
} from "lucide-react";
import { clsx } from "clsx";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { supabase } from "@/lib/supabase";
import { useTheme } from "@/components/ThemeProvider";

export type NavTab = "oracle" | "libraire" | "guide";

// ── Feedback ──────────────────────────────────────────────────────────────────

function FeedbackPanel({ sessionId }: { sessionId: string }) {
  const [hovered, setHovered] = useState(0);
  const [selected, setSelected] = useState(0);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

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
      <div className="px-4 py-4 flex flex-col items-center gap-2 text-center animate-fade-up">
        <CheckCircle2 size={20} className="text-emerald-400" />
        <p className="text-xs text-[var(--text-muted)]">
          Merci pour ton retour !
        </p>
      </div>
    );
  }

  return (
    <div className="px-4 py-4 space-y-3">
      <p className="text-[10px] text-[var(--text-subtle)] uppercase tracking-wider">
        Évaluer cette conversation
      </p>
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
              fill={
                (hovered || selected) >= star ? "var(--gold)" : "transparent"
              }
              stroke={
                (hovered || selected) >= star
                  ? "var(--gold)"
                  : "var(--text-subtle)"
              }
            />
          </button>
        ))}
        {selected > 0 && (
          <span className="ml-2 text-xs text-[var(--gold)]">
            {
              ["", "Mauvais", "Passable", "Correct", "Bien", "Excellent"][
                selected
              ]
            }
          </span>
        )}
      </div>
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
            {submitting ? (
              "Envoi…"
            ) : (
              <>
                <Send size={11} className="mr-1" /> Envoyer
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

// ── Types & helpers ───────────────────────────────────────────────────────────

interface Session {
  session_id: string;
  title: string;
  updated_at: string;
  provider: string;
  model: string;
}

interface Props {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  isAdmin: boolean;
  firstName: string;
  lastName: string;
  email: string;
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

const NAV_ITEMS: {
  id: NavTab;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}[] = [
  { id: "oracle", label: "Oracle", icon: MessageSquare },
  { id: "libraire", label: "Librairie", icon: BookOpen },
  { id: "guide", label: "Guide", icon: HelpCircle },
];

// ── Main component ────────────────────────────────────────────────────────────

export function SessionSidebar({
  activeTab,
  onTabChange,
  activeSessionId,
  onSelectSession,
  onNewSession,
  isAdmin,
  firstName,
  lastName,
  email,
}: Props) {
  const { theme, toggle } = useTheme();
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [provider, setProvider] = useState("groq");
  const [model, setModel] = useState("llama-3.3-70b-versatile");
  const [temperature, setTemperature] = useState("0");
  const [kFinal, setKFinal] = useState("5");

  useEffect(() => {
    setProvider(localStorage.getItem("oracle_provider") || "groq");
    setModel(localStorage.getItem("oracle_model") || "llama-3.3-70b-versatile");
    setTemperature(localStorage.getItem("oracle_temperature") || "0");
    setKFinal(localStorage.getItem("oracle_k_final") || "5");
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) throw new Error();
      const data = await res.json();
      setSessions(data.sessions ?? []);
    } catch {
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const deleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm("Supprimer cette conversation ?")) return;
    await fetch(`/api/sessions/${id}`, { method: "DELETE" });
    setSessions((prev) => prev.filter((s) => s.session_id !== id));
    if (activeSessionId === id) onNewSession();
  };

  async function handleLogout() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  const initials =
    firstName && lastName
      ? `${firstName[0]}${lastName[0]}`
      : firstName
        ? firstName.slice(0, 2)
        : email.slice(0, 2);

  const displayName = firstName
    ? lastName
      ? `${firstName} ${lastName}`
      : firstName
    : email.split("@")[0];

  return (
    <div className="flex flex-col h-full bg-[var(--surface)]">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-[var(--border)] flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[var(--gold)] text-xl leading-none">◈</span>
          <span className="font-cinzel text-sm font-semibold text-[var(--text)] tracking-widest uppercase">
            L'Oracle
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="px-2 pt-3 pb-2 space-y-0.5 flex-shrink-0">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={clsx(
              "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150",
              activeTab === id
                ? "bg-[var(--gold-glow)] text-[var(--gold)] border border-[var(--gold)]/20 font-medium"
                : "text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-subtle)] border border-transparent",
            )}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
        {isAdmin && (
          <>
            <Separator className="bg-[var(--border)] my-1" />
            <button
              onClick={() => router.push("/admin")}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm border border-transparent text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-subtle)] transition-all duration-150"
            >
              <Shield size={15} />
              Administration
            </button>
          </>
        )}
      </nav>

      <Separator className="bg-[var(--border)] mx-2 flex-shrink-0" />

      {/* Sessions — oracle tab only */}
      {activeTab === "oracle" ? (
        <>
          <div className="px-2 pt-2 pb-2 flex-shrink-0">
            <Button
              onClick={onNewSession}
              className="w-full bg-[var(--gold-glow)] hover:bg-[var(--gold)]/15 text-[var(--gold)] border border-[var(--gold)]/30 hover:border-[var(--gold)]/50 font-medium text-xs gap-2 h-8"
              variant="outline"
            >
              <MessageSquarePlus size={13} />
              Nouvelle conversation
            </Button>
          </div>
          <Separator className="bg-[var(--border)] flex-shrink-0" />

          <div className="flex-1 overflow-y-auto py-1 min-h-0">
            {loading && (
              <div className="px-4 py-6 flex justify-center gap-1">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-[var(--border)] animate-bounce"
                    style={{ animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </div>
            )}
            {!loading && sessions.length === 0 && (
              <div className="px-4 py-8 text-center space-y-2">
                <MessageSquarePlus
                  size={22}
                  className="mx-auto text-[var(--text-subtle)] opacity-40"
                />
                <p className="text-xs text-[var(--text-subtle)]">
                  Aucune conversation
                </p>
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
                  <p
                    className={clsx(
                      "text-[13px] truncate pr-6 leading-snug",
                      activeSessionId === s.session_id
                        ? "text-[var(--text)] font-medium"
                        : "text-[var(--text)]",
                    )}
                  >
                    {s.title || "Conversation sans titre"}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <Clock size={9} className="text-[var(--text-subtle)]" />
                    <span className="text-[10px] text-[var(--text-subtle)]">
                      {mounted ? timeAgo(s.updated_at) : "…"}
                    </span>
                    {s.provider && (
                      <Badge
                        variant="outline"
                        className="text-[9px] h-4 px-1 border-[var(--border)] text-[var(--text-subtle)] ml-auto"
                      >
                        {s.provider}
                      </Badge>
                    )}
                  </div>
                  <button
                    onClick={(e) => deleteSession(e, s.session_id)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded opacity-0 group-hover:opacity-100 text-[var(--text-subtle)] hover:text-red-400 transition-all duration-150"
                    aria-label="Supprimer"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {activeSessionId && (
            <>
              <Separator className="bg-[var(--border)]" />
              <FeedbackPanel sessionId={activeSessionId} />
            </>
          )}
        </>
      ) : (
        <div className="flex-1" />
      )}

      {/* Settings panel — full width, above footer */}
      {settingsOpen && (
        <div className="border-t border-[var(--border)] px-3 py-3 space-y-2 flex-shrink-0 animate-fade-up bg-[var(--surface)]">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-subtle)]">
            Paramètres actifs
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            <div className="bg-[var(--bg-subtle)] rounded-lg px-2.5 py-2 space-y-0.5">
              <div className="flex items-center gap-1 text-[9px] text-[var(--text-subtle)] uppercase tracking-wider">
                <Cpu size={9} /> Provider
              </div>
              <p className="text-xs font-medium text-[var(--text)] capitalize">
                {provider}
              </p>
            </div>
            <div className="bg-[var(--bg-subtle)] rounded-lg px-2.5 py-2 space-y-0.5">
              <div className="flex items-center gap-1 text-[9px] text-[var(--text-subtle)] uppercase tracking-wider">
                <Thermometer size={9} /> Temp.
              </div>
              <p className="text-xs font-medium text-[var(--text)]">
                {temperature}
              </p>
            </div>
          </div>
          <div className="bg-[var(--bg-subtle)] rounded-lg px-2.5 py-2 space-y-0.5">
            <p className="text-[9px] text-[var(--text-subtle)] uppercase tracking-wider">
              Modèle
            </p>
            <p className="text-[11px] font-medium text-[var(--text)] truncate">
              {model}
            </p>
          </div>
          <div className="bg-[var(--bg-subtle)] rounded-lg px-2.5 py-2 space-y-0.5">
            <p className="text-[9px] text-[var(--text-subtle)] uppercase tracking-wider">
              Sources RAG (k)
            </p>
            <p className="text-xs font-medium text-[var(--text)]">
              {kFinal} chunks
            </p>
          </div>
        </div>
      )}

      {/* User footer */}
      <div className="border-t border-[var(--border)] px-3 py-3 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          {/* Avatar */}
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-[var(--gold-glow)] border border-[var(--gold)]/25 flex items-center justify-center">
            <span className="text-[var(--gold)] text-xs font-semibold uppercase leading-none">
              {initials.toUpperCase()}
            </span>
          </div>

          {/* Name + email */}
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-[var(--text)] truncate leading-tight">
              {displayName}
            </p>
            <p className="text-[10px] text-[var(--text-subtle)] truncate leading-tight">
              {email}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-0.5 flex-shrink-0">
            <button
              onClick={() => setSettingsOpen((v) => !v)}
              className={clsx(
                "p-1.5 rounded-lg transition-colors",
                settingsOpen
                  ? "bg-[var(--gold-glow)] text-[var(--gold)]"
                  : "text-[var(--text-subtle)] hover:text-[var(--text)] hover:bg-[var(--bg-subtle)]",
              )}
              aria-label="Paramètres actifs"
            >
              <Settings size={14} />
            </button>
            <button
              onClick={toggle}
              className="p-1.5 rounded-lg text-[var(--text-subtle)] hover:text-[var(--text)] hover:bg-[var(--bg-subtle)] transition-colors"
              aria-label="Changer le thème"
            >
              {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
            </button>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-[var(--text-subtle)] hover:text-red-400 hover:bg-red-500/5 transition-colors"
              aria-label="Se déconnecter"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
