export interface AgentQLQueryDataResponse {
  data: Record<string, unknown>
  metadata?: {
    request_id?: string
    screenshot?: string | null
  }
}

export class AgentQLClient {
  constructor(
    private readonly apiKey: string | undefined,
    private readonly baseUrl = "https://api.agentql.com/v1"
  ) {}

  async queryPageByPrompt(input: { prompt: string; url?: string; html?: string }): Promise<AgentQLQueryDataResponse> {
    if (!this.apiKey) {
      throw new Error("No API keys added.")
    }

    if (!input.url && !input.html) {
      throw new Error("AgentQL requires either a page URL or HTML.")
    }

    const response = await fetch(`${this.baseUrl}/query-data`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "X-API-Key": this.apiKey
      },
      body: JSON.stringify({
        prompt: input.prompt,
        ...(input.url ? { url: input.url } : {}),
        ...(input.html ? { html: input.html } : {}),
        params: {
          wait_for: 0,
          is_scroll_to_bottom_enabled: false,
          mode: "fast",
          is_screenshot_enabled: false,
          browser_profile: "light"
        }
      })
    })

    return parseJsonResponse<AgentQLQueryDataResponse>(response, "AgentQL query-data")
  }
}

async function parseJsonResponse<T>(response: Response, label: string): Promise<T> {
  const text = await response.text()
  if (!response.ok) {
    throw new Error(`${label} failed with ${response.status}: ${text || response.statusText}`)
  }

  return JSON.parse(text) as T
}
