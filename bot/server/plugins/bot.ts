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
  await (bot as any).ensureInitialized();
  const discordAdapter = (bot as any).getAdapter('discord');
  if (discordAdapter?.startGatewayListener) {
    const fakeEvent = { waitUntil: (p: Promise<any>) => p.catch((e: unknown) => console.error('[Gateway]', e)) };
    const result = discordAdapter.startGatewayListener(fakeEvent);
    if (result instanceof Response) result.text().then((t: string) => console.log('[Gateway response]', t));
  }

  console.log("[HELMo Oracle Bot] Initialized ✓");
});
