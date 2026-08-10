import type { AIMessage, AIProvider } from "~/types/providers"
import type { ArgusProviderSettings, PrimaryAIProvider } from "~/settings/ProviderSettings"
import { getProviderApiKey } from "~/settings/providerCatalog"

export class HttpAIProvider implements AIProvider {
  readonly name: PrimaryAIProvider
  private readonly apiKey: string
  private readonly model: string

  constructor(settings: ArgusProviderSettings) {
    this.name = settings.primaryProvider
    const apiKey = getProviderApiKey(settings)
    if (!apiKey) {
      throw new Error("No API keys added.")
    }

    this.apiKey = apiKey
    this.model = settings.selectedModel
  }

  async complete(messages: AIMessage[]): Promise<string> {
    switch (this.name) {
      case "openai":
        return this.completeOpenAI("https://api.openai.com/v1/chat/completions", messages)
      case "groq":
        return this.completeOpenAI("https://api.groq.com/openai/v1/chat/completions", messages)
      case "claude":
        return this.completeClaude(messages)
      case "gemini":
        return this.completeGemini(messages)
      default:
        throw new Error("No API keys added.")
    }
  }

  private async completeOpenAI(endpoint: string, messages: AIMessage[]): Promise<string> {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: this.model,
        messages,
        temperature: 0.1
      })
    })

    const json = (await parseJsonResponse(response, this.name)) as { choices?: Array<{ message?: { content?: string } }>; error?: { message?: string } }
    if (!response.ok) {
      throw new Error(json.error?.message ?? `${this.name} request failed with ${response.status}.`)
    }

    return json.choices?.[0]?.message?.content ?? ""
  }

  private async completeClaude(messages: AIMessage[]): Promise<string> {
    const system = messages.find((message) => message.role === "system")?.content
    const claudeMessages = messages
      .filter((message) => message.role !== "system")
      .map((message) => ({ role: message.role === "assistant" ? "assistant" : "user", content: message.content }))

    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": this.apiKey,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true"
      },
      body: JSON.stringify({
        model: this.model,
        max_tokens: 1200,
        temperature: 0.1,
        ...(system ? { system } : {}),
        messages: claudeMessages
      })
    })

    const json = (await parseJsonResponse(response, "Claude")) as { content?: Array<{ type: string; text?: string }>; error?: { message?: string } }
    if (!response.ok) {
      throw new Error(json.error?.message ?? `Claude request failed with ${response.status}.`)
    }

    return json.content?.find((part) => part.type === "text")?.text ?? ""
  }

  private async completeGemini(messages: AIMessage[]): Promise<string> {
    const prompt = messages.map((message) => `${message.role.toUpperCase()}: ${message.content}`).join("\n\n")
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(this.model)}:generateContent?key=${encodeURIComponent(this.apiKey)}`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.1 }
        })
      }
    )

    const json = (await parseJsonResponse(response, "Gemini")) as { candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>; error?: { message?: string } }
    if (!response.ok) {
      throw new Error(json.error?.message ?? `Gemini request failed with ${response.status}.`)
    }

    return json.candidates?.[0]?.content?.parts?.[0]?.text ?? ""
  }
}

async function parseJsonResponse(response: Response, label: string): Promise<unknown> {
  const text = await response.text()
  try {
    return JSON.parse(text)
  } catch {
    if (!response.ok) {
      throw new Error(`${label} request failed with ${response.status}: ${text || response.statusText}`)
    }

    return {}
  }
}
