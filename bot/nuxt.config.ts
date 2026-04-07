// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },

  // Bot-only: no SSR frontend needed
  ssr: false,

  nitro: {
    // Allow async tasks to outlive the HTTP response (needed for Discord gateway)
    experimental: {
      tasks: true,
    },
  },

  runtimeConfig: {
    // Server-only secrets (never exposed to client)
    discordBotToken: process.env.DISCORD_BOT_TOKEN ?? '',
    discordPublicKey: process.env.DISCORD_PUBLIC_KEY ?? '',
    discordApplicationId: process.env.DISCORD_APPLICATION_ID ?? '',
    redisUrl: process.env.REDIS_URL ?? 'redis://localhost:6379',
    groqApiKey: process.env.GROQ_API_KEY ?? '',
    anthropicApiKey: process.env.ANTHROPIC_API_KEY ?? '', // optionnel
    mcpServerUrl: process.env.MCP_SERVER_URL ?? 'http://localhost:8000/mcp/sse',
  },
})

