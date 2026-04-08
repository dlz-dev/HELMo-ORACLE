"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

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
};

export const PROVIDERS = Object.keys(
  PROVIDER_MODELS,
) as (keyof typeof PROVIDER_MODELS)[];

export const LS = {
  provider: "oracle_provider",
  model: "oracle_model",
  temperature: "oracle_temperature",
  k_final: "oracle_k_final",
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
    <Card className="border-[var(--border)] bg-[var(--surface)] animate-fade-up overflow-hidden">
      <CardHeader className="p-0">
        <Button
          variant="ghost"
          onClick={() => setOpen((v) => !v)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-[var(--bg-subtle)] rounded-none h-auto text-left"
        >
          <span className="text-sm font-medium text-[var(--text)]">
            {title}
          </span>
          {open ? (
            <ChevronUp size={14} className="text-[var(--text-muted)]" />
          ) : (
            <ChevronDown size={14} className="text-[var(--text-muted)]" />
          )}
        </Button>
      </CardHeader>
      {open && (
        <CardContent className="px-5 pb-5 border-t border-[var(--border)] space-y-4 pt-4">
          {children}
        </CardContent>
      )}
    </Card>
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
