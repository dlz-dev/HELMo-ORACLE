import { createBrowserClient } from "@supabase/ssr";

const LOCAL_MODE = process.env.NEXT_PUBLIC_LOCAL_MODE === "true";

const mockClient = {
  auth: {
    onAuthStateChange: () => ({
      data: { subscription: { unsubscribe: () => {} } },
    }),
    signOut: async () => {},
    signInAnonymously: async () => ({ error: null }),
    signInWithPassword: async () => ({ error: null }),
    signUp: async () => ({ data: { user: null }, error: null }),
    getUser: async () => ({ data: { user: { id: "local_user" } } }),
  },
  from: () => ({
    select: () => ({
      eq: () => ({
        single: () => Promise.resolve({ data: { role: "admin" } }),
      }),
    }),
    update: () => ({ eq: () => Promise.resolve({ error: null }) }),
    insert: () => Promise.resolve({ error: null }),
  }),
} as unknown as ReturnType<typeof createBrowserClient>;

export const supabase = LOCAL_MODE
  ? mockClient
  : createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    );
