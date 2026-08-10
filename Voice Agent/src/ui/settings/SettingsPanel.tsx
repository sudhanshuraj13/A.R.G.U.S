import { useEffect, useMemo, useState } from "react"
import { ProviderSettingsStore, type ArgusProviderSettings, type PrimaryAIProvider } from "~/settings/ProviderSettings"
import { getDefaultModel, getProviderOption, PROVIDER_OPTIONS } from "~/settings/providerCatalog"
import { useArgusStore } from "~/state/argusStore"

export function SettingsPanel() {
  const settings = useArgusStore((state) => state.settings)
  const setSettings = useArgusStore((state) => state.setSettings)
  const notify = useArgusStore((state) => state.notify)
  const [isSaving, setIsSaving] = useState(false)
  const store = useMemo(() => new ProviderSettingsStore(), [])
  const selectedProvider = getProviderOption(settings.primaryProvider)

  useEffect(() => {
    void store.load().then(setSettings)
  }, [setSettings, store])

  const update = (patch: Partial<ArgusProviderSettings>) => {
    setSettings({ ...settings, ...patch })
  }

  const updateProvider = (primaryProvider: PrimaryAIProvider) => {
    setSettings({
      ...settings,
      primaryProvider,
      selectedModel: getDefaultModel(primaryProvider)
    })
  }

  const save = async () => {
    setIsSaving(true)
    try {
      await store.save(settings)
      notify({ type: "success", message: "Provider settings saved locally." })
    } catch (error) {
      notify({ type: "error", message: error instanceof Error ? error.message : "Could not save settings." })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section className="border-b border-argus-line px-4 py-3">
      <h2 className="text-sm font-semibold">Settings</h2>
      <div className="mt-3 space-y-3">
        <label className="block text-xs font-medium text-gray-600" htmlFor="argus-provider">
          Primary AI provider
        </label>
        <select
          id="argus-provider"
          className="w-full rounded-md border border-argus-line bg-white px-3 py-2 text-sm"
          value={settings.primaryProvider}
          onChange={(event) => updateProvider(event.target.value as PrimaryAIProvider)}
        >
          {PROVIDER_OPTIONS.map((provider) => (
            <option key={provider.value} value={provider.value}>
              {provider.label}
            </option>
          ))}
        </select>

        <label className="block text-xs font-medium text-gray-600" htmlFor="argus-model">
          Model
        </label>
        <select
          id="argus-model"
          className="w-full rounded-md border border-argus-line bg-white px-3 py-2 text-sm"
          value={settings.selectedModel}
          onChange={(event) => update({ selectedModel: event.target.value })}
        >
          {selectedProvider.models.map((model) => (
            <option key={model.id} value={model.id}>
              {model.label}
            </option>
          ))}
        </select>

        {selectedProvider.apiKeyField && selectedProvider.apiKeyLabel ? (
          <SecretInput
            label={selectedProvider.apiKeyLabel}
            value={settings[selectedProvider.apiKeyField]}
            onChange={(value) => update({ [selectedProvider.apiKeyField as string]: value } as Partial<ArgusProviderSettings>)}
          />
        ) : null}

        <details className="rounded-md border border-argus-line px-3 py-2">
          <summary className="cursor-pointer text-sm font-medium">Automation API keys</summary>
          <div className="mt-3 space-y-3">
            <SecretInput label="AgentQL API key" value={settings.agentqlApiKey} onChange={(agentqlApiKey) => update({ agentqlApiKey })} />
            <SecretInput label="TinyFish API key" value={settings.tinyfishApiKey} onChange={(tinyfishApiKey) => update({ tinyfishApiKey })} />
          </div>
        </details>

        <button
          type="button"
          onClick={save}
          className="w-full rounded-md bg-argus-ink px-3 py-2 text-sm font-medium text-white"
          disabled={isSaving}
        >
          {isSaving ? "Saving" : "Save settings"}
        </button>
      </div>
    </section>
  )
}

interface SecretInputProps {
  label: string
  value?: string | undefined
  onChange(value: string | undefined): void
}

function SecretInput({ label, value, onChange }: SecretInputProps) {
  const id = label.toLowerCase().replace(/\s+/g, "-")

  return (
    <div>
      <label className="block text-xs font-medium text-gray-600" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        type="password"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value.trim() || undefined)}
        className="mt-1 w-full rounded-md border border-argus-line px-3 py-2 text-sm outline-none focus:border-argus-accent"
        autoComplete="off"
      />
    </div>
  )
}
