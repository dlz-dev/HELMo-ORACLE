/**
 * GET /api/discord/gateway
 *
 * Lance la connexion WebSocket Gateway de Discord (mode bot classique).
 * Nécessaire pour recevoir les messages dans les salons normaux,
 * en complément du webhook qui gère les slash commands / interactions.
 *
 * Cette route est rappelée toutes les 9 minutes par le cron Vercel
 * (vercel.json) pour maintenir la connexion active.
 *
 * Durée max : ~10 minutes (limite des fonctions serverless Vercel).
 */

import { getBot } from "../../lib/bot";

export default defineEventHandler(async (event) => {
  const bot = getBot();
  const discordAdapter = (bot as any).adapters?.discord;

  if (!discordAdapter?.startGatewayListener) {
    throw createError({
      statusCode: 503,
      message: "Discord adapter not available or does not support gateway mode.",
    });
  }

  // startGatewayListener maintient la connexion WS ouverte jusqu'au timeout serverless
  event.waitUntil(discordAdapter.startGatewayListener(event));

  return { status: "Gateway started" };
});
