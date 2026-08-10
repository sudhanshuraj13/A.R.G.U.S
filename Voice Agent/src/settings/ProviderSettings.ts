import { getDefaultModel } from "./providerCatalog"

export type PrimaryAIProvider = "openai" | "gemini" | "claude" | "groq" | "mock"

export interface ArgusProviderSettings {
  primaryProvider: PrimaryAIProvider
  selectedModel: string
  openaiApiKey?: string | undefined
  geminiApiKey?: string | undefined
  claudeApiKey?: string | undefined
  groqApiKey?: string | undefined
  agentqlApiKey?: string | undefined
  tinyfishApiKey?: string | undefined
  executionMode: "local" | "remote"
}

export const DEFAULT_PROVIDER_SETTINGS: ArgusProviderSettings = {
  primaryProvider: "mock",
  selectedModel: "offline-rule-based",
  executionMode: "local"
}

const STORAGE_KEY = "argus.providerSettings"

export class ProviderSettingsStore {
  async load(): Promise<ArgusProviderSettings> {
    if (!globalThis.chrome?.storage?.local) {
      return DEFAULT_PROVIDER_SETTINGS
    }

    const result = await chrome.storage.local.get(STORAGE_KEY)
    const loaded = {
      ...DEFAULT_PROVIDER_SETTINGS,
      ...((result[STORAGE_KEY] as Partial<ArgusProviderSettings> | undefined) ?? {})
    }

    return {
      ...loaded,
      selectedModel: loaded.selectedModel || getDefaultModel(loaded.primaryProvider)
    }
  }

  async save(settings: ArgusProviderSettings): Promise<void> {
    if (!globalThis.chrome?.storage?.local) {
      return
    }

    await chrome.storage.local.set({ [STORAGE_KEY]: settings })
  }
}
