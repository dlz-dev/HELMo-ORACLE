"use client";

import { clsx } from "clsx";
import { User, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Props {
  role:      "user" | "assistant";
  content:   string;
  index:     number;
  isLast:    boolean;
  isLoading: boolean;
}

export function ChatMessage({ role, content, index, isLast, isLoading }: Props) {
  const isUser = role === "user";

  return (
    <div
      className={clsx(
        "flex gap-3 animate-fade-up",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
      style={{ animationDelay: `${Math.min(index * 20, 200)}ms` }}
    >
      {/* Avatar */}
      <div
        className={clsx(
          "flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mt-0.5",
          isUser
            ? "bg-subtle border border-default"
            : "bg-gold-glow border border-gold/20"
        )}
      >
        {isUser
          ? <User size={13} className="text-muted-fg" />
          : <Sparkles size={13} className="text-gold" />
        }
      </div>

      {/* Bulle */}
      <div
        className={clsx(
          "max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed",
          isUser
            ? "bg-subtle text-main rounded-tr-sm border border-default"
            : "bg-surface text-main rounded-tl-sm border border-default shadow-card"
        )}
      >
        {/* Indicateur de streaming */}
        {isLoading && isLast && !content ? (
          <div className="flex items-center gap-1.5 h-5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-gold/60 animate-bounce"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none
            prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-headings:my-2
            prose-strong:text-main prose-code:text-gold prose-code:bg-subtle
            prose-code:px-1 prose-code:rounded prose-code:text-xs">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}