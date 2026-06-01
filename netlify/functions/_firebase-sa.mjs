/**
 * _firebase-sa.mjs
 * Helper centralisé pour récupérer le service account Firebase.
 *
 * Stratégie:
 *   1. Tente Netlify Blobs (norah-config / firebase-sa) — recommandé
 *   2. Fallback: env var FIREBASE_SA_B64
 * Cache en mémoire pour éviter les lectures répétées dans la même invocation.
 *
 * Usage:
 *   import { getServiceAccount } from "./_firebase-sa.mjs";
 *   const sa = await getServiceAccount();
 *   // sa.client_email, sa.private_key, sa.project_id
 */

let _saCache = null;

export async function getServiceAccount() {
  if (_saCache) return _saCache;

  // 1) Tentative via Netlify Blobs
  try {
    const { getStore } = await import("@netlify/blobs");
    const store = getStore("norah-config");
    const saJson = await store.get("firebase-sa");
    if (saJson) {
      _saCache = JSON.parse(saJson);
      return _saCache;
    }
  } catch (_e) {
    // Continue vers fallback
  }

  // 2) Fallback: env var (compatibilité)
  const b64 = process.env.FIREBASE_SA_B64;
  if (!b64) throw new Error("Service account not found (no blob, no env var)");
  const saJson = atob(b64);
  _saCache = JSON.parse(saJson);
  return _saCache;
}
