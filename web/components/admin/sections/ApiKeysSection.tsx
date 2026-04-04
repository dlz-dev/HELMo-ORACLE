"use client";

import { CheckCircle, Save } from "lucide-react";
import { Section, Field, inputClass } from "./shared";
import { Button } from "@/components/ui/button";

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
      <Button
        onClick={onSave}
        className="w-full bg-[var(--gold)] hover:bg-[var(--gold-light)] text-[#0a0c10] text-sm font-medium"
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
      </Button>
    </Section>
  );
}
