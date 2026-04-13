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

  // Sur Digital Ocean (process persistant), on démarre la gateway en boucle
  await (bot as any).ensureInitialized();
  const discordAdapter = (bot as any).getAdapter('discord');
  if (discordAdapter?.startGatewayListener) {
    const keepGatewayAlive = async () => {
      let delay = 5000;
      const MAX_DELAY = 5 * 60 * 1000; // 5 minutes max
      while (true) {
        try {
          console.log('[Gateway] Démarrage...');
          delay = 5000; // reset si la session a bien démarré
          const fakeEvent = { waitUntil: (p: Promise<any>) => p.catch((e: unknown) => console.error('[Gateway]', e)) };
          await discordAdapter.startGatewayListener(fakeEvent);
          console.log(`[Gateway] Session terminée, reconnexion dans ${delay / 1000}s...`);
        } catch (e) {
          console.error(`[Gateway] Erreur, reconnexion dans ${delay / 1000}s...`, e);
        }
        await new Promise(resolve => setTimeout(resolve, delay));
        delay = Math.min(delay * 2, MAX_DELAY); // backoff exponentiel
      }
    };
    keepGatewayAlive();
  }

  console.log("[HELMo Oracle Bot] Initialized ✓");
});
