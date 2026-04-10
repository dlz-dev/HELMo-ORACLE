"use client";

import { useState, useEffect } from "react";
import { useMediaQuery } from "react-responsive";
import { SessionSidebar } from "./SessionSidebar";
import { ChatWindow } from "./ChatWindow";
import { PanelLeftOpen, PanelLeftClose } from "lucide-react";
import { supabase } from "@/lib/supabase";

export function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isGuest, setIsGuest] = useState(false);
  const isMobile = useMediaQuery({ query: "(max-width: 768px)" });

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setIsGuest(!data.user);
    });
  }, []);

  useEffect(() => {
    if (isMobile) setSidebarOpen(false);
    else setSidebarOpen(true);
  }, [isMobile]);

  return (
    <div className="flex w-full h-full overflow-hidden">
      {/* Sidebar sessions */}
      <aside
        className={`
          flex-shrink-0 border-r border-default bg-surface
          transition-all duration-300 ease-in-out overflow-y-auto
          ${sidebarOpen ? "w-64" : "w-0"}
        `}
      >
        <SessionSidebar
          activeSessionId={sessionId}
          onSelectSession={(id) => {
            setSessionId(id);
            if (isMobile) setSidebarOpen(false);
          }}
          onNewSession={() => {
            setSessionId(null);
            if (isMobile) setSidebarOpen(false);
          }}
        />
      </aside>

      {/* Zone principale */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Toggle sidebar */}
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

        <ChatWindow
          sessionId={sessionId}
          onSessionCreated={setSessionId}
          isGuest={isGuest}
        />
      </div>
    </div>
  );
}
