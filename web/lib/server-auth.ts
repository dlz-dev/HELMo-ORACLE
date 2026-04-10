import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

const LOCAL_MODE = process.env.NEXT_PUBLIC_LOCAL_MODE === "true";

/**
 * Returns the user ID from the server-side session.
 * In local mode, returns a fixed "local_user" ID (no auth required).
 */
export async function getServerUserId(): Promise<string | null> {
  if (LOCAL_MODE) {
    return "00000000-0000-0000-0000-000000000001";
  }

  const cookieStore = await cookies();
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: () => {},
      },
    },
  );
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user?.id ?? null;
}
