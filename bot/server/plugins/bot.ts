/**
 * Plugin Nuxt server-side — s'exécute une seule fois au démarrage de Nitro.
 * Initialise le bot avec les secrets du runtimeConfig.
 */

import { initBot } from "~/server/lib/bot";

export default defineNitroPlugin(async () => {
  const config = useRuntimeConfig();

  await initBot({
    mcpServerUrl: config.mcpServerUrl,
    groqApiKey: config.groqApiKey,
    anthropicApiKey: config.anthropicApiKey || undefined,
  });

  console.log("[HELMo Oracle Bot] Initialized ✓");
});
