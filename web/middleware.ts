import { NextRequest, NextResponse } from "next/server";

/**
 * Middleware Next.js — protection de la route /admin.
 * En prod, remplacer par une vraie auth (Supabase Auth, NextAuth, etc.)
 * Pour l'instant, la protection est gérée côté client dans AdminPanel.tsx
 * (vérification du mot de passe NEXT_PUBLIC_ADMIN_PASSWORD).
 */
export function middleware(_req: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*"],
};
