import type { ArgusProviderSettings } from "./ProviderSettings"
import { getProviderApiKey } from "./providerCatalog"

export function getMissingApiKeys(settings: ArgusProviderSettings): string[] {
  const missing: string[] = []

  if (settings.primaryProvider === "mock" || !getProviderApiKey(settings)) {
    missing.push("AI provider")
  }

  if (!settings.agentqlApiKey) {
    missing.push("AgentQL")
  }

  if (!settings.tinyfishApiKey) {
    missing.push("TinyFish")
  }

  return missing
}

export function requireApiKeys(settings: ArgusProviderSettings): void {
  const missing = getMissingApiKeys(settings)
  if (missing.length > 0) {
    throw new Error(`No API keys added. Missing: ${missing.join(", ")}.`)
  }
}
