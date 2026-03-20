"use client";

import { Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { Section, Field, inputClass } from "./shared";

interface Props {
  provider: string;
  model: string;
  temperature: number;
  testMsg: string;
  testState: "idle" | "running" | "success" | "error";
  testOutput: string;
  onMsgChange: (msg: string) => void;
  onTest: () => void;
}

export function TestSection({
  provider,
  model,
  temperature,
  testMsg,
  testState,
  testOutput,
  onMsgChange,
  onTest,
}: Props) {
  return (
    <Section title="Test du Provider" defaultOpen={false}>
      <Field label="Message de test">
        <textarea
          value={testMsg}
          onChange={(e) => onMsgChange(e.target.value)}
          className={clsx(inputClass, "resize-none h-20")}
        />
      </Field>
      <button
        onClick={onTest}
        disabled={testState === "running"}
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
      >
        {testState === "running" ? (
          <>
            <Loader2 size={13} className="animate-spin" /> Test en cours…
          </>
        ) : (
          <>🧪 Tester le provider</>
        )}
      </button>
      {testState !== "idle" && (
        <div
          className={clsx(
            "mt-3 p-3 rounded-lg text-xs font-mono whitespace-pre-wrap break-words",
            testState === "success" &&
              "bg-green-400/10 text-green-300 border border-green-400/30",
            testState === "error" &&
              "bg-red-400/10 text-red-300 border border-red-400/30",
            testState === "running" &&
              "bg-blue-400/10 text-blue-300 border border-blue-400/30",
          )}
        >
          {testOutput}
        </div>
      )}
    </Section>
  );
}
