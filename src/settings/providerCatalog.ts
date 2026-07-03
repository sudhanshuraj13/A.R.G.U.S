import type { ArgusProviderSettings, PrimaryAIProvider } from "./ProviderSettings"

export interface ProviderModelOption {
  id: string
  label: string
}

export interface ProviderOption {
  value: PrimaryAIProvider
  label: string
  apiKeyField?: keyof Pick<ArgusProviderSettings, "openaiApiKey" | "geminiApiKey" | "claudeApiKey" | "groqApiKey">
  apiKeyLabel?: string
  models: ProviderModelOption[]
}

export const PROVIDER_OPTIONS: ProviderOption[] = [
  {
    value: "mock",
    label: "Mock / offline",
    models: [{ id: "offline-rule-based", label: "Offline rule-based planner" }]
  },
  {
    value: "openai",
    label: "OpenAI",
    apiKeyField: "openaiApiKey",
    apiKeyLabel: "OpenAI API key",
    models: [
      { id: "gpt-5.2", label: "GPT-5.2" },
      { id: "gpt-5-mini", label: "GPT-5 mini" },
      { id: "gpt-5-nano", label: "GPT-5 nano" },
      { id: "gpt-4.1", label: "GPT-4.1" }
    ]
  },
  {
    value: "gemini",
    label: "Gemini",
    apiKeyField: "geminiApiKey",
    apiKeyLabel: "Gemini API key",
    models: [
      { id: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
      { id: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
      { id: "gemini-2.0-flash", label: "Gemini 2.0 Flash" }
    ]
  },
  {
    value: "claude",
    label: "Claude",
    apiKeyField: "claudeApiKey",
    apiKeyLabel: "Claude API key",
    models: [
      { id: "claude-opus-4-1-20250805", label: "Claude Opus 4.1" },
      { id: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
      { id: "claude-3-7-sonnet-20250219", label: "Claude 3.7 Sonnet" }
    ]
  },
  {
    value: "groq",
    label: "Groq",
    apiKeyField: "groqApiKey",
    apiKeyLabel: "Groq API key",
    models: [
      { id: "openai/gpt-oss-120b", label: "GPT-OSS 120B" },
      { id: "openai/gpt-oss-20b", label: "GPT-OSS 20B" },
      { id: "llama-3.1-8b-instant", label: "Llama 3.1 8B Instant" },
      { id: "qwen/qwen3-32b", label: "Qwen3 32B" }
    ]
  }
]

const FALLBACK_PROVIDER = PROVIDER_OPTIONS[0] as ProviderOption

export function getProviderOption(provider: PrimaryAIProvider): ProviderOption {
  return PROVIDER_OPTIONS.find((option) => option.value === provider) ?? FALLBACK_PROVIDER
}

export function getDefaultModel(provider: PrimaryAIProvider): string {
  return getProviderOption(provider).models[0]?.id ?? "offline-rule-based"
}

export function getProviderApiKey(settings: ArgusProviderSettings): string | undefined {
  const option = getProviderOption(settings.primaryProvider)
  return option.apiKeyField ? settings[option.apiKeyField] : undefined
}
