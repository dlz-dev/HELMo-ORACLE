"use client";

import { useEffect, useRef, useState } from "react";
import { getSourceContent } from "@/lib/api";

interface Props {
  filename: string;
  passage: string;
  onClose: () => void;
}

export function SourceViewer({ filename, passage, onClose }: Props) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const highlightRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    setContent(null);
    setError(false);
    getSourceContent(filename)
      .then(setContent)
      .catch(() => setError(true));
  }, [filename]);

  useEffect(() => {
    if (content && highlightRef.current) {
      highlightRef.current.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [content]);

  const findPassage = (text: string): number => {
    const trimmed = passage.trim();
    // Try progressively shorter needles (80 → 40 → 20 chars)
    for (const len of [80, 40, 20]) {
      const needle = trimmed.slice(0, len);
      if (!needle) break;
      const idx = text.indexOf(needle);
      if (idx !== -1) return idx;
    }
    // Last resort: normalize whitespace on both sides
    const norm = (s: string) => s.replace(/\s+/g, " ");
    const normContent = norm(text);
    const normNeedle = norm(trimmed).slice(0, 40);
    return normContent.indexOf(normNeedle);
  };

  const renderContent = () => {
    if (error)
      return (
        <p className="text-xs text-red-400 text-center py-8">
          Fichier introuvable sur le serveur.
        </p>
      );
    if (!content)
      return (
        <p className="text-xs text-[var(--text-subtle)] text-center py-8">
          Chargement...
        </p>
      );

    const idx = findPassage(content);

    if (idx === -1) {
      return (
        <pre className="text-xs text-[var(--text)] whitespace-pre-wrap font-mono leading-relaxed">
          {content}
        </pre>
      );
    }

    const highlightEnd = idx + passage.trim().length;
    return (
      <pre className="text-xs text-[var(--text)] whitespace-pre-wrap font-mono leading-relaxed">
        {content.slice(0, idx)}
        <span
          ref={highlightRef}
          className="bg-amber-400/50 text-amber-900 dark:text-amber-100 rounded px-0.5"
        >
          {content.slice(idx, highlightEnd)}
        </span>
        {content.slice(highlightEnd)}
      </pre>
    );
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative z-10 w-[80vw] max-w-4xl h-[80vh] flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl">
        <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)]">
          <span className="text-sm text-[var(--gold)] font-mono truncate max-w-[90%]">
            {filename}
          </span>
          <button
            onClick={onClose}
            className="text-[var(--text-subtle)] hover:text-[var(--text)] text-lg leading-none"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto p-4">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
