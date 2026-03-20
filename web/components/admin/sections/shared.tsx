"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

export const inputClass = `w-full px-3 py-2 rounded-lg border border-default bg-surface-alt text-sm text-main
  placeholder:text-subtle-fg focus:outline-none focus:border-gold/50 transition-colors duration-150`;

export const PROVIDER_MODELS: Record<string, string[]> = {
  groq: [
    "llama-3.3-70b-versatile",
    "compound-beta",
    "moonshotai/kimi-k2-instruct-0905",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "deepseek-r1-distill-llama-70b",
  ],
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
  anthropic: ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
  gemini: ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
  ollama: ["llama3.1", "mistral", "gemma3:12b", "deepseek-r1:8b"],
};

export const PROVIDERS = Object.keys(
  PROVIDER_MODELS,
) as (keyof typeof PROVIDER_MODELS)[];

export const LS = {
  provider: "oracle_provider",
  model: "oracle_model",
  temperature: "oracle_temperature",
  k_final: "oracle_k_final",
  apiKeys: "oracle_api_keys",
};

export function Section({
  title,
  children,
  defaultOpen = true,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-default rounded-xl overflow-hidden bg-surface animate-fade-up">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-subtle transition-colors duration-150 text-left"
      >
        <span className="text-sm font-medium text-main">{title}</span>
        {open ? (
          <ChevronUp size={14} className="text-muted-fg" />
        ) : (
          <ChevronDown size={14} className="text-muted-fg" />
        )}
      </button>
      {open && (
        <div className="px-5 pb-5 border-t border-default space-y-4 pt-4">
          {children}
        </div>
      )}
    </div>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-fg uppercase tracking-wide">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-subtle-fg">{hint}</p>}
    </div>
  );
}
