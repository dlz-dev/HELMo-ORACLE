"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";

const LOCAL_MODE = process.env.NEXT_PUBLIC_LOCAL_MODE === "true";

const ROLES = [
  { value: "etudiant", label: "Étudiant" },
  { value: "professeur", label: "Professeur" },
  { value: "entreprise", label: "Entreprise" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState("etudiant");
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  if (LOCAL_MODE) {
    return (
      <div className="min-h-[calc(100vh-56px)] flex items-center justify-center px-4">
        <Card className="w-full max-w-sm border-[var(--border)] bg-[var(--surface)] shadow-lg text-center">
          <CardContent className="pt-10 pb-8 space-y-4">
            <span className="text-[var(--gold)] text-4xl block">◈</span>
            <h1 className="font-cinzel text-xl font-semibold text-[var(--text)] tracking-widest uppercase">
              Oracle
            </h1>
            <p className="text-[var(--text-muted)] text-sm">
              Mode local activé
            </p>
            <Badge
              variant="outline"
              className="text-[10px] border-[var(--gold)]/30 text-[var(--gold)]"
            >
              Authentification désactivée
            </Badge>
            <Button
              onClick={() => router.push("/")}
              className="w-full mt-2 bg-[var(--gold)] hover:bg-[var(--gold-light)] text-[#0a0c10] font-medium"
            >
              Accéder à l'Oracle
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  async function handleGuest() {
    setLoading(true);
    const { error } = await supabase.auth.signInAnonymously();
    if (error) setError(error.message);
    else window.location.href = "/";
    setLoading(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    if (mode === "login") {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) setError(error.message);
      else window.location.href = "/";
    } else {
      const { data, error } = await supabase.auth.signUp({ email, password });
      if (error) setError(error.message);
      else if (data.user) {
        await supabase
          .from("profiles")
          .update({ role, first_name: firstName, last_name: lastName })
          .eq("id", data.user.id);
        setSuccess("Compte créé ! Vérifie ton email pour confirmer.");
      }
    }
    setLoading(false);
  }

  return (
    <div className="min-h-[calc(100vh-56px)] flex items-center justify-center px-4 bg-[var(--bg)]">
      <div className="w-full max-w-sm space-y-4 animate-fade-up">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-[var(--gold-glow)] border border-[var(--gold)]/20 mb-1">
            <span className="text-[var(--gold)] text-2xl">◈</span>
          </div>
          <h1 className="font-cinzel text-xl font-semibold text-[var(--text)] tracking-widest uppercase">
            Oracle
          </h1>
          <p className="text-[var(--text-muted)] text-sm">
            {mode === "login"
              ? "Connecte-toi pour accéder aux archives"
              : "Crée ton compte"}
          </p>
        </div>

        <Card className="border-[var(--border)] bg-[var(--surface)] shadow-md">
          <CardContent className="pt-6 pb-6 px-6 space-y-4">
            {/* Email form */}
            <form onSubmit={handleSubmit} className="space-y-3">
              {/* Name fields (signup only) */}
              {mode === "signup" && (
                <div className="flex gap-2">
                  <div className="flex-1 space-y-1">
                    <label className="text-[10px] text-[var(--text-subtle)] uppercase tracking-wide">
                      Prénom
                    </label>
                    <Input
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      required
                      placeholder="Prénom"
                      className="bg-[var(--bg-subtle)] border-[var(--border)] text-[var(--text)] placeholder:text-[var(--text-subtle)] h-9 text-sm"
                    />
                  </div>
                  <div className="flex-1 space-y-1">
                    <label className="text-[10px] text-[var(--text-subtle)] uppercase tracking-wide">
                      Nom
                    </label>
                    <Input
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      required
                      placeholder="Nom"
                      className="bg-[var(--bg-subtle)] border-[var(--border)] text-[var(--text)] placeholder:text-[var(--text-subtle)] h-9 text-sm"
                    />
                  </div>
                </div>
              )}

              <div className="space-y-1">
                <label className="text-[10px] text-[var(--text-subtle)] uppercase tracking-wide">
                  Email
                </label>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="ton@email.com"
                  className="bg-[var(--bg-subtle)] border-[var(--border)] text-[var(--text)] placeholder:text-[var(--text-subtle)] h-9 text-sm"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] text-[var(--text-subtle)] uppercase tracking-wide">
                  Mot de passe
                </label>
                <div className="relative">
                  <Input
                    type={showPass ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="••••••••"
                    className="bg-[var(--bg-subtle)] border-[var(--border)] text-[var(--text)] placeholder:text-[var(--text-subtle)] h-9 text-sm pr-9"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-subtle)] hover:text-[var(--text)]"
                  >
                    {showPass ? <EyeOff size={13} /> : <Eye size={13} />}
                  </button>
                </div>
              </div>

              {/* Role (signup only) */}
              {mode === "signup" && (
                <div className="space-y-1">
                  <label className="text-[10px] text-[var(--text-subtle)] uppercase tracking-wide">
                    Profil
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full h-9 px-3 rounded-md border border-[var(--border)] bg-[var(--bg-subtle)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--gold)]/50 transition-colors"
                  >
                    {ROLES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {error && (
                <p className="text-xs text-red-400 bg-red-400/8 border border-red-400/20 px-3 py-2 rounded-md">
                  {error}
                </p>
              )}
              {success && (
                <p className="text-xs text-emerald-400 bg-emerald-400/8 border border-emerald-400/20 px-3 py-2 rounded-md">
                  {success}
                </p>
              )}

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-[var(--gold)] hover:bg-[var(--gold-light)] text-[#0a0c10] font-medium"
              >
                {loading ? (
                  <Loader2 size={14} className="animate-spin mr-2" />
                ) : null}
                {mode === "login" ? "Se connecter" : "Créer le compte"}
              </Button>
            </form>

            {/* Mode toggle */}
            <p className="text-center text-xs text-[var(--text-subtle)]">
              {mode === "login" ? "Pas encore de compte ?" : "Déjà un compte ?"}{" "}
              <button
                onClick={() => {
                  setMode(mode === "login" ? "signup" : "login");
                  setError("");
                  setSuccess("");
                }}
                className="text-[var(--gold)] hover:underline font-medium"
              >
                {mode === "login" ? "S'inscrire" : "Se connecter"}
              </button>
            </p>

            <Separator className="bg-[var(--border)]" />

            {/* Guest */}
            <Button
              type="button"
              variant="ghost"
              onClick={handleGuest}
              disabled={loading}
              className="w-full text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-subtle)] text-xs h-8"
            >
              Continuer en tant qu'invité
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
