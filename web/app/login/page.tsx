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

  async function handleGoogleLogin() {
    setLoading(true);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) {
      setError(error.message);
      setLoading(false);
    }
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
            {/* Google Login Button */}
            <Button
              variant="outline"
              onClick={handleGoogleLogin}
              disabled={loading}
              className="w-full border-[var(--border)] bg-[var(--bg-subtle)] hover:bg-[var(--bg-subtle)]/80 text-[var(--text)] h-10 flex items-center justify-center gap-3 transition-all duration-300 hover:border-[var(--gold)]/40 hover:shadow-[0_0_15px_rgba(212,175,55,0.1)] group"
            >
              {loading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <div className="bg-white p-1 rounded-sm group-hover:scale-110 transition-transform duration-300">
                  <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      fill="#4285F4"
                    />
                    <path
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      fill="#34A853"
                    />
                    <path
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      fill="#FBBC05"
                    />
                    <path
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 12-4.53z"
                      fill="#EA4335"
                    />
                  </svg>
                </div>
              )}
              <span className="text-sm font-medium tracking-wide">Continuer avec Google</span>
            </Button>

            <div className="relative py-2">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-[var(--border)]/50"></div>
              </div>
              <div className="relative flex justify-center text-[10px] uppercase tracking-[0.2em]">
                <span className="bg-[var(--surface)] px-3 text-[var(--text-subtle)] font-medium">
                  Ou par email
                </span>
              </div>
            </div>

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
