"use client";

import { useState } from "react";
import { SessionSidebar } from "./SessionSidebar";
import { ChatWindow } from "./ChatWindow";
import { PanelLeftOpen, PanelLeftClose } from "lucide-react";

export function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);

  return (
    <div className="flex w-full h-full overflow-hidden">
      {/* Sidebar sessions */}
      <aside
        className={`
          flex-shrink-0 border-r border-default bg-surface
          transition-all duration-200 ease-in-out overflow-hidden
          ${sidebarOpen ? "w-64" : "w-0"}
        `}
      >
        <SessionSidebar
          activeSessionId={sessionId}
          onSelectSession={setSessionId}
          onNewSession={() => setSessionId(null)}
        />
      </aside>

      {/* Zone principale */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Toggle sidebar */}
        <button
          onClick={() => setSidebarOpen((v) => !v)}
          className="absolute top-3 left-3 z-10 p-1.5 rounded-md text-muted-fg hover:text-main hover:bg-subtle transition-all duration-150"
          aria-label={sidebarOpen ? "Fermer le panneau" : "Ouvrir le panneau"}
        >
          {sidebarOpen ? (
            <PanelLeftClose size={16} />
          ) : (
            <PanelLeftOpen size={16} />
          )}
        </button>

        <ChatWindow sessionId={sessionId} onSessionCreated={setSessionId} />
      </div>
    </div>
  );
}
