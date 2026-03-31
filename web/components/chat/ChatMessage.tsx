"use client";

import { useState } from "react";
import { clsx } from "clsx";
import { User, Sparkles, Copy, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Props {
  role: "user" | "assistant";
  content: string;
  index: number;
  isLast: boolean;
  isLoading: boolean;
}

export function ChatMessage({ role, content, index, isLast, isLoading }: Props) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div
      className={clsx(
        "group flex gap-3 animate-fade-up",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
      style={{ animationDelay: `${Math.min(index * 20, 200)}ms` }}
    >
      {/* Avatar */}
      <div
        className={clsx(
          "flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mt-0.5",
          isUser
            ? "bg-[var(--bg-subtle)] border border-[var(--border)]"
            : "bg-[var(--gold-glow)] border border-[var(--gold)]/20",
        )}
      >
        {isUser ? (
          <User size={13} className="text-[var(--text-muted)]" />
        ) : (
          <Sparkles size={13} className="text-[var(--gold)]" />
        )}
      </div>

      {/* Bubble + actions */}
      <div className={clsx("flex flex-col gap-1", isUser ? "items-end" : "items-start", "max-w-[75%]")}>
        <div
          className={clsx(
            "px-4 py-3 rounded-2xl text-sm leading-relaxed",
            isUser
              ? "bg-[var(--bg-subtle)] text-[var(--text)] rounded-tr-sm border border-[var(--border)]"
              : "bg-[var(--surface)] text-[var(--text)] rounded-tl-sm border border-[var(--border)] shadow-[var(--shadow-sm)]",
          )}
        >
          {/* Streaming dots */}
          {isLoading && isLast && !content ? (
            <div className="flex items-center gap-1.5 h-5">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-[var(--gold)]/60 animate-bounce"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none
              prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-headings:my-2
              prose-strong:text-[var(--text)] prose-code:text-[var(--gold)]
              prose-code:bg-[var(--bg-subtle)] prose-code:px-1.5 prose-code:rounded
              prose-code:text-xs prose-code:before:content-none prose-code:after:content-none">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Copy button — assistant only, visible on hover */}
        {!isUser && content && !isLoading && (
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-[var(--text-subtle)]
                       opacity-0 group-hover:opacity-100 hover:text-[var(--text)] hover:bg-[var(--bg-subtle)]
                       transition-all duration-150"
          >
            {copied ? (
              <><Check size={10} className="text-emerald-400" /> Copié</>
            ) : (
              <><Copy size={10} /> Copier</>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
