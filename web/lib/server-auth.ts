import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

/**
 * Returns the Supabase user ID from the server-side session cookie.
 * Used in API route handlers to identify the authenticated user.
 */
export async function getServerUserId(): Promise<string | null> {
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
