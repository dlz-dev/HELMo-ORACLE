"use client";

import { CheckCircle, Save } from "lucide-react";
import {
  Section,
  Field,
  inputClass,
  PROVIDERS,
  PROVIDER_MODELS,
} from "./shared";
import { Button } from "@/components/ui/button";

interface Props {
  provider: string;
  model: string;
  temperature: number;
  kFinal: number;
  saveStatus: "idle" | "saved";
  onProviderChange: (p: string) => void;
  onModelChange: (m: string) => void;
  onTemperatureChange: (t: number) => void;
  onKFinalChange: (k: number) => void;
  onSave: () => void;
}

export function ModelSection({
  provider,
  model,
  temperature,
  kFinal,
  saveStatus,
  onProviderChange,
  onModelChange,
  onTemperatureChange,
  onKFinalChange,
  onSave,
}: Props) {
  return (
    <Section title="Modèle IA">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Provider">
          <select
            value={provider}
            onChange={(e) => {
              onProviderChange(e.target.value);
              onModelChange(PROVIDER_MODELS[e.target.value]?.[0] ?? "");
            }}
            className={inputClass}
          >
            {PROVIDERS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Modèle">
          <select
            value={model}
            onChange={(e) => onModelChange(e.target.value)}
            className={inputClass}
          >
            {(PROVIDER_MODELS[provider] ?? []).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field
        label={`Température — ${temperature}`}
        hint="0 = déterministe · 1 = créatif"
      >
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={temperature}
          onChange={(e) => onTemperatureChange(parseFloat(e.target.value))}
          className="w-full accent-gold"
        />
      </Field>

      <Field
        label={`K final (chunks RAG) — ${kFinal}`}
        hint="Nombre de chunks retournés par la recherche"
      >
        <input
          type="range"
          min={1}
          max={15}
          step={1}
          value={kFinal}
          onChange={(e) => onKFinalChange(parseInt(e.target.value))}
          className="w-full accent-gold"
        />
      </Field>

      <Button
        onClick={onSave}
        className="w-full bg-[var(--gold)] hover:bg-[var(--gold-light)] text-[#0a0c10] text-sm font-medium"
      >
        {saveStatus === "saved" ? (
          <>
            <CheckCircle size={13} /> Sauvegardé !
          </>
        ) : (
          <>
            <Save size={13} /> Sauvegarder la configuration
          </>
        )}
      </Button>
    </Section>
  );
}
