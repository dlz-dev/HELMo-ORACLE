"use client";

import { User, Mail, Shield, LogOut, Calendar } from "lucide-react";
import { Section, Field } from "./shared";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface Props {
  user: any;
  onLogout: () => void;
}

export function ProfileSection({ user, onLogout }: Props) {
  if (!user) return null;

  const createdAt = user.created_at
    ? new Date(user.created_at).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "Inconnue";

  return (
    <div className="space-y-6">
      <Section title="Mon Compte">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="border-[var(--border)] bg-[var(--bg-subtle)]">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-[var(--gold-glow)] border border-[var(--gold)]/20 flex items-center justify-center">
                  <User size={24} className="text-[var(--gold)]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[var(--text)]">
                    Identifiant
                  </p>
                  <p className="text-xs text-[var(--text-subtle)] font-mono truncate max-w-[200px]">
                    {user.id}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-[var(--border)] bg-[var(--bg-subtle)]">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                  <Mail size={24} className="text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[var(--text)]">
                    Email
                  </p>
                  <p className="text-xs text-[var(--text-subtle)]">
                    {user.email || "Non renseigné"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-[var(--border)] bg-[var(--bg-subtle)]">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <Shield size={24} className="text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[var(--text)]">Rôle</p>
                  <p className="text-xs text-[var(--text-subtle)]">
                    Administrateur
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-[var(--border)] bg-[var(--bg-subtle)]">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                  <Calendar size={24} className="text-amber-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[var(--text)]">
                    Membre depuis
                  </p>
                  <p className="text-xs text-[var(--text-subtle)]">
                    {createdAt}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8 pt-6 border-t border-[var(--border)]">
          <Button
            variant="outline"
            onClick={onLogout}
            className="border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/50"
          >
            <LogOut size={16} className="mr-2" />
            Se déconnecter
          </Button>
        </div>
      </Section>
    </div>
  );
}
