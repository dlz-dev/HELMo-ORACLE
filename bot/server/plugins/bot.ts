/**
 * Plugin Nuxt server-side — s'exécute une seule fois au démarrage de Nitro.
 * Initialise le bot avec les secrets du runtimeConfig.
 */

import { initBot } from '~~/server/lib/bot';

export default defineNitroPlugin(async () => {
  const config = useRuntimeConfig();

  // Attendre que le backend soit prêt
  await new Promise(resolve => setTimeout(resolve, 10000));

  const bot = await initBot({
    mcpServerUrl: config.mcpServerUrl,
    groqApiKey: config.groqApiKey,
    anthropicApiKey: config.anthropicApiKey || undefined,
  });

  // Sur Digital Ocean (process persistant), on démarre la gateway immédiatement
  const discordAdapter = (bot as any).adapters?.discord;
  if (discordAdapter?.startGateway) {
    discordAdapter.startGateway().catch((err: unknown) => {
      console.error("[HELMo Oracle Bot] Gateway error:", err);
    });
  }

  console.log("[HELMo Oracle Bot] Initialized ✓");
});
