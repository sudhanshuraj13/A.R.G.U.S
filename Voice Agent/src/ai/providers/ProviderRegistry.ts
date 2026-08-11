import type { AIProvider } from "~/types/providers"
import { MockProvider } from "./MockProvider"

export type ProviderName = AIProvider["name"]

export class ProviderRegistry {
  private readonly providers = new Map<ProviderName, AIProvider>()

  constructor(defaultProviders: AIProvider[] = [new MockProvider()]) {
    defaultProviders.forEach((provider) => this.providers.set(provider.name, provider))
  }

  register(provider: AIProvider): void {
    this.providers.set(provider.name, provider)
  }

  get(name: ProviderName = "mock"): AIProvider {
    const provider = this.providers.get(name)
    if (!provider) {
      throw new Error(`AI provider ${name} is not registered.`)
    }

    return provider
  }

  has(name: ProviderName): boolean {
    return this.providers.has(name)
  }
}
