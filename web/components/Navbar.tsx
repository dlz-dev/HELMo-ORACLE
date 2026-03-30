"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Moon,
  Sun,
  BookOpen,
  MessageSquare,
  Settings,
  LogOut,
} from "lucide-react";
import { useTheme } from "./ThemeProvider";
import { clsx } from "clsx";
import { supabase } from "@/lib/supabase";
import { useEffect, useState } from "react";

const LOCAL_MODE = process.env.NEXT_PUBLIC_LOCAL_MODE === "true";

const BASE_NAV_LINKS = [
  { href: "/", label: "Oracle", icon: MessageSquare },
  { href: "/sources", label: "Sources", icon: BookOpen },
];

const ALL_NAV_LINKS = [
  ...BASE_NAV_LINKS,
  { href: "/admin", label: "Admin", icon: Settings },
];

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, toggle } = useTheme();
  const [isAdmin, setIsAdmin] = useState(LOCAL_MODE);

  useEffect(() => {
    if (LOCAL_MODE) return;
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session?.user) {
        setIsAdmin(false);
        return;
      }
      supabase
        .from("profiles")
        .select("role")
        .eq("id", session.user.id)
        .single()
        .then(({ data }) => setIsAdmin(data?.role === "admin"));
    });
    return () => subscription.unsubscribe();
  }, []);

  const navLinks = isAdmin ? ALL_NAV_LINKS : BASE_NAV_LINKS;

  async function handleLogout() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <header
      className="sticky top-0 z-50 border-b border-default bg-surface/80 backdrop-blur-md"
      style={{ boxShadow: "var(--shadow-sm)" }}
    >
      <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          {/* Rune décorative */}
          <span
            className="text-gold text-lg leading-none select-none transition-all duration-300 group-hover:opacity-80"
            aria-hidden
          >
            ◈
          </span>
          <span className="font-oracle text-base font-semibold text-main tracking-widest uppercase">
            Oracle
          </span>
        </Link>

        {/* Navigation centrale */}
        <nav className="hidden sm:flex items-center gap-1">
          {navLinks.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-all duration-150",
                  active
                    ? "text-gold bg-gold-glow font-medium"
                    : "text-muted-fg hover:text-main hover:bg-subtle",
                )}
              >
                <Icon size={14} strokeWidth={1.8} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Actions droite */}
        <div className="flex items-center gap-1">
          <button
            onClick={toggle}
            aria-label="Changer de thème"
            className="p-2 rounded-md text-muted-fg hover:text-main hover:bg-subtle transition-all duration-150"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          {!LOCAL_MODE && (
            <button
              onClick={handleLogout}
              aria-label="Se déconnecter"
              className="p-2 rounded-md text-muted-fg hover:text-main hover:bg-subtle transition-all duration-150"
            >
              <LogOut size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Ligne dorée sous la navbar — très subtile */}
      <div className="gold-line" />
    </header>
  );
}
