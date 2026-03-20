"use client";

import { CheckCircle, Save } from "lucide-react";
import { Section, Field, inputClass } from "./shared";

interface Props {
  apiKeys: Record<string, string>;
  saveStatus: "idle" | "saved";
  onChange: (provider: string, value: string) => void;
  onSave: () => void;
}

export function ApiKeysSection({
  apiKeys,
  saveStatus,
  onChange,
  onSave,
}: Props) {
  return (
    <Section title="Clés API" defaultOpen={false}>
      <p className="text-xs text-muted-fg">
        Les clés sont stockées localement dans votre navigateur.
      </p>
      {Object.keys(apiKeys).map((p) => (
        <Field key={p} label={p}>
          <input
            type="password"
            value={apiKeys[p]}
            onChange={(e) => onChange(p, e.target.value)}
            placeholder={`Clé ${p}…`}
            className={inputClass}
          />
        </Field>
      ))}
      <button
        onClick={onSave}
        className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-gold text-white text-sm font-medium hover:bg-gold-light transition-colors duration-150"
      >
        {saveStatus === "saved" ? (
          <>
            <CheckCircle size={13} /> Clés sauvegardées !
          </>
        ) : (
          <>
            <Save size={13} /> Sauvegarder les clés
          </>
        )}
      </button>
    </Section>
  );
}
