"use client";

import { type ChangeEvent, type FormEvent, useRef } from "react";
import { ArrowUp, Loader2 } from "lucide-react";

interface Props {
  value:      string;
  onChange:   (e: ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmit:   (e: FormEvent<HTMLFormElement>) => void;
  isLoading:  boolean;
}

export function ChatInput({ value, onChange, onSubmit, isLoading }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Entrée seule = envoyer, Shift+Entrée = saut de ligne
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isLoading) {
        const form = textareaRef.current?.closest("form") as HTMLFormElement;
        form?.requestSubmit();
      }
    }
  };

  // Auto-resize du textarea
  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const canSubmit = value.trim().length > 0 && !isLoading;

  return (
    <form onSubmit={onSubmit} className="relative">
      <div className="flex items-end gap-2 rounded-xl border border-default bg-surface
                      focus-within:border-gold/40 transition-colors duration-150
                      px-3 py-2">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Pose ta question sur Dofus…"
          rows={1}
          disabled={isLoading}
          className="flex-1 resize-none bg-transparent text-sm text-main placeholder:text-subtle-fg
                     focus:outline-none disabled:opacity-50 leading-relaxed min-h-[22px]"
          style={{ maxHeight: "160px" }}
        />

        <button
          type="submit"
          disabled={!canSubmit}
          className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center
                     bg-gold text-white transition-all duration-150
                     hover:bg-gold-light disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Envoyer"
        >
          {isLoading
            ? <Loader2 size={13} className="animate-spin" />
            : <ArrowUp size={13} strokeWidth={2.5} />
          }
        </button>
      </div>

      <p className="text-center text-xs text-subtle-fg mt-1.5">
        Entrée pour envoyer · Shift+Entrée pour un saut de ligne
      </p>
    </form>
  );
}