"use client";

import { type ChangeEvent, type FormEvent, useRef } from "react";
import { ArrowUp, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  value: string;
  onChange: (e: ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  children?: React.ReactNode; // Pour injecter le bouton CoT depuis ChatWindow
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  isLoading,
  children,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isLoading) {
        const form = textareaRef.current?.closest("form") as HTMLFormElement;
        form?.requestSubmit();
      }
    }
  };

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const MAX_CHARS = 300;
  const canSubmit =
    value.trim().length > 0 && !isLoading && value.length <= MAX_CHARS;

  return (
    <form onSubmit={onSubmit} className="relative">
      <div
        className="flex items-end gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)]
                      focus-within:border-[var(--gold)]/40 transition-colors duration-150 px-3 py-2"
      >
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Pose ta question…"
          rows={1}
          disabled={isLoading}
          className="flex-1 resize-none bg-transparent border-0 shadow-none text-sm
                     text-[var(--text)] placeholder:text-[var(--text-subtle)]
                     focus-visible:ring-0 focus-visible:ring-offset-0
                     disabled:opacity-50 leading-relaxed min-h-[22px] p-0"
          style={{ maxHeight: "160px" }}
        />

        {/* Slot pour injecter le bouton CoT */}
        {children}

        <Button
          type="submit"
          disabled={!canSubmit}
          size="icon"
          className="flex-shrink-0 w-7 h-7 rounded-lg bg-[var(--gold)] hover:bg-[var(--gold-light)]
                     text-[#0a0c10] disabled:opacity-30"
          aria-label="Envoyer"
        >
          {isLoading ? (
            <Loader2 size={13} className="animate-spin" />
          ) : (
            <ArrowUp size={13} strokeWidth={2.5} />
          )}
        </Button>
      </div>
      <p className="text-center text-xs text-[var(--text-subtle)] mt-1.5">
        Entrée pour envoyer · Shift+Entrée pour un saut de ligne
        {value.length > MAX_CHARS * 0.8 && (
          <span
            className={
              value.length > MAX_CHARS ? " text-red-400" : " text-yellow-400"
            }
          >
            {" "}
            · {value.length}/{MAX_CHARS}
          </span>
        )}
      </p>
    </form>
  );
}
