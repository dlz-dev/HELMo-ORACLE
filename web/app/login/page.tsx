"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

const ROLES = [
  { value: "etudiant", label: "Étudiant" },
  { value: "professeur", label: "Professeur" },
  { value: "entreprise", label: "Entreprise" },
];

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState("etudiant");
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  async function handleGuest() {
    setLoading(true);
    const { error } = await supabase.auth.signInAnonymously();
    if (error) setError(error.message);
    else {
      window.location.href = "/";
    }
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
      if (error) {
        setError(error.message);
      } else {
        window.location.href = "/";
      }
    } else {
      const { data, error } = await supabase.auth.signUp({ email, password });
      if (error) {
        setError(error.message);
      } else if (data.user) {
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
    <div className="min-h-[calc(100vh-56px)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-gold text-3xl">◈</span>
          <h1 className="font-oracle text-2xl font-semibold text-main tracking-widest uppercase mt-2">
            Oracle
          </h1>
          <p className="text-muted-fg text-sm mt-1">
            {mode === "login"
              ? "Connecte-toi pour accéder aux archives"
              : "Crée ton compte"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-muted-fg mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-md border border-default bg-surface text-main text-sm focus:outline-none focus:border-gold transition-colors"
              placeholder="ton@email.com"
            />
          </div>

          {mode === "signup" && (
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-sm text-muted-fg mb-1">
                  Prénom
                </label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-md border border-default bg-surface text-main text-sm focus:outline-none focus:border-gold transition-colors"
                  placeholder="Prénom"
                />
              </div>
              <div className="flex-1">
                <label className="block text-sm text-muted-fg mb-1">Nom</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-md border border-default bg-surface text-main text-sm focus:outline-none focus:border-gold transition-colors"
                  placeholder="Nom"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm text-muted-fg mb-1">
              Mot de passe
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-md border border-default bg-surface text-main text-sm focus:outline-none focus:border-gold transition-colors"
              placeholder="••••••••"
            />
          </div>

          {mode === "signup" && (
            <div>
              <label className="block text-sm text-muted-fg mb-1">Profil</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-2 rounded-md border border-default bg-surface text-main text-sm focus:outline-none focus:border-gold transition-colors"
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {error && <p className="text-red-400 text-sm">{error}</p>}
          {success && <p className="text-green-400 text-sm">{success}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded-md bg-gold text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading
              ? "..."
              : mode === "login"
                ? "Se connecter"
                : "Créer le compte"}
          </button>
        </form>

        <p className="text-center text-sm text-muted-fg mt-4">
          {mode === "login" ? "Pas encore de compte ?" : "Déjà un compte ?"}{" "}
          <button
            onClick={() => {
              setMode(mode === "login" ? "signup" : "login");
              setError("");
            }}
            className="text-gold hover:underline"
          >
            {mode === "login" ? "S'inscrire" : "Se connecter"}
          </button>
        </p>

        <div className="relative my-4">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-default" />
          </div>
          <div className="relative flex justify-center text-xs text-muted-fg">
            <span className="bg-page px-2">ou</span>
          </div>
        </div>

        <button
          onClick={handleGuest}
          disabled={loading}
          className="w-full py-2 rounded-md border border-default text-muted-fg text-sm hover:text-main hover:border-gold transition-colors disabled:opacity-50"
        >
          Continuer en tant qu'invité
        </button>
      </div>
    </div>
  );
}
