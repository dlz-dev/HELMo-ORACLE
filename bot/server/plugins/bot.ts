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
      while (true) {
        try {
          console.log('[Gateway] Démarrage...');
          // Capturer la vraie promesse de connexion via waitUntil
          let gatewayPromise: Promise<any> | null = null;
          const fakeEvent = {
            waitUntil: (p: Promise<any>) => {
              gatewayPromise = p.catch((e: unknown) => console.error('[Gateway error]', e));
            }
          };
          discordAdapter.startGatewayListener(fakeEvent);
          if (gatewayPromise) {
            await gatewayPromise; // attend la vraie fin de session (3 min)
          } else {
            await new Promise(resolve => setTimeout(resolve, 180000));
          }
          console.log('[Gateway] Session terminée, reconnexion dans 30s...');
        } catch (e) {
          console.error('[Gateway] Erreur, reconnexion dans 60s...', e);
          await new Promise(resolve => setTimeout(resolve, 60000));
        }
        await new Promise(resolve => setTimeout(resolve, 30000));
      }
    };
    keepGatewayAlive();
  }

  console.log("[HELMo Oracle Bot] Initialized ✓");
});
