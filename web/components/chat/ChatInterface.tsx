"use client";

import { useState, useEffect } from "react";
import { useMediaQuery } from "react-responsive";
import { SessionSidebar, type NavTab } from "./SessionSidebar";
import { ChatWindow } from "./ChatWindow";
import { PanelLeftOpen, PanelLeftClose } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { SourcesGrid } from "@/components/sources/SourcesGrid";

const LOCAL_MODE = process.env.NEXT_PUBLIC_LOCAL_MODE === "true";

// ── Guide ─────────────────────────────────────────────────────────────────────

const GUIDE_TIPS = [
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-5 h-5 text-[var(--gold)] flex-shrink-0 mt-0.5"
      >
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
      </svg>
    ),
    title: "Soyez précis dans votre question",
    body: 'Plus votre question est spécifique, meilleure sera la réponse. Plutôt que "comment jouer Iop ?", préférez "quelles sont les meilleures caractéristiques pour un Iop full air niveau 200 ?"',
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-5 h-5 text-[var(--gold)] flex-shrink-0 mt-0.5"
      >
        <path d="M3 3v18h18" />
        <path d="m19 9-5 5-4-4-3 3" />
      </svg>
    ),
    title: "Contextualisez votre niveau",
    body: "Indiquez votre niveau de jeu, votre classe et votre progression. Oracle adaptera ses réponses à votre profil — débutant ou vétéran, solo ou en équipe.",
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-5 h-5 text-[var(--gold)] flex-shrink-0 mt-0.5"
      >
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
    title: "Utilisez un langage naturel",
    body: "Aucun besoin de formuler en mots-clés. Posez votre question comme vous la poseriez à un expert de Dofus — Oracle comprend le français courant.",
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-5 h-5 text-[var(--gold)] flex-shrink-0 mt-0.5"
      >
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.35-4.35M11 8v6M8 11h6" />
      </svg>
    ),
    title: "Demandez des précisions",
    body: 'Si une réponse vous semble incomplète, demandez "expliquez en détail" ou "donnez un exemple concret". L\'Oracle peut approfondir n\'importe quel sujet.',
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-5 h-5 text-[var(--gold)] flex-shrink-0 mt-0.5"
      >
        <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
    title: "Enchaînez les questions",
    body: "Oracle conserve le contexte de la conversation. Vous pouvez affiner progressivement une réponse en posant des questions complémentaires sans tout répéter.",
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-5 h-5 text-[var(--gold)] flex-shrink-0 mt-0.5"
      >
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
    ),
    title: "Consultez les sources",
    body: "Après une réponse, l'icône Librairie vous permet de voir quelles archives ont été consultées et d'évaluer la pertinence des sources utilisées.",
  },
] as const;

function GuideContent() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-10 pt-14">
        <div className="text-center mb-10 space-y-2">
          <h1 className="font-cinzel text-2xl font-semibold text-[var(--text)] tracking-wide">
            Guide d'utilisation
          </h1>
          <p className="text-sm text-[var(--text-muted)]">
            Tirez le meilleur de Oracle en suivant ces recommandations
          </p>
        </div>
        <div className="space-y-3">
          {GUIDE_TIPS.map(({ icon, title, body }) => (
            <div
              key={title}
              className="flex gap-4 p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--gold)]/25 transition-colors duration-150"
            >
              {icon}
              <div className="space-y-1.5">
                <h3 className="font-semibold text-sm text-[var(--text)]">
                  {title}
                </h3>
                <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                  {body}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Librairie ─────────────────────────────────────────────────────────────────

function LibraireContent() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8 pt-14">
        <div className="text-center mb-8 space-y-2">
          <h1 className="font-cinzel text-2xl font-semibold text-[var(--text)] tracking-wide">
            Librairie
          </h1>
          <p className="text-sm text-[var(--text-muted)]">
            Les sources de connaissance consultées par Oracle
          </p>
        </div>
        <SourcesGrid />
      </div>
    </div>
  );
}

// ── ChatInterface ─────────────────────────────────────────────────────────────

export function ChatInterface() {
  const [activeTab, setActiveTab] = useState<NavTab>("oracle");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isGuest, setIsGuest] = useState(false);
  const [isAdmin, setIsAdmin] = useState(LOCAL_MODE);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const isMobile = useMediaQuery({ query: "(max-width: 768px)" });

  useEffect(() => {
    if (isMobile) setSidebarOpen(false);
    else setSidebarOpen(true);
  }, [isMobile]);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      const user = data.user;
      setIsGuest(!user);
      setEmail(user?.email || "");
      if (user && !LOCAL_MODE) {
        supabase
          .from("profiles")
          .select("first_name, last_name, role")
          .eq("id", user.id)
          .single()
          .then(({ data: profile }) => {
            if (profile?.first_name) setFirstName(profile.first_name);
            if (profile?.last_name) setLastName(profile.last_name);
            if (profile?.role === "admin") setIsAdmin(true);
          });
      }
    });
  }, []);

  return (
    <div className="flex w-full h-full overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`
          flex-shrink-0 border-r border-default bg-surface
          transition-all duration-300 ease-in-out overflow-hidden
          ${sidebarOpen ? "w-64" : "w-0"}
        `}
      >
        <SessionSidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          activeSessionId={sessionId}
          onSelectSession={(id) => {
            setSessionId(id);
            setActiveTab("oracle");
            if (isMobile) setSidebarOpen(false);
          }}
          onNewSession={() => {
            setSessionId(null);
            setActiveTab("oracle");
            if (isMobile) setSidebarOpen(false);
          }}
          isAdmin={isAdmin}
          firstName={firstName}
          lastName={lastName}
          email={email}
        />
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Sidebar toggle */}
        <button
          onClick={() => setSidebarOpen((v) => !v)}
          className="absolute top-3 left-3 z-10 p-1.5 rounded-md text-muted-fg hover:text-main hover:bg-subtle transition-all"
          aria-label={sidebarOpen ? "Fermer le panneau" : "Ouvrir le panneau"}
        >
          {sidebarOpen ? (
            <PanelLeftClose size={16} />
          ) : (
            <PanelLeftOpen size={16} />
          )}
        </button>

        {activeTab === "oracle" && (
          <ChatWindow
            sessionId={sessionId}
            onSessionCreated={setSessionId}
            isGuest={isGuest}
            firstName={firstName}
          />
        )}
        {activeTab === "libraire" && <LibraireContent />}
        {activeTab === "guide" && <GuideContent />}
      </div>
    </div>
  );
}
