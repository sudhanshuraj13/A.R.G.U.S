export interface TinyFishSearchResult {
  position?: number
  site_name?: string
  title: string
  url: string
  snippet?: string
}

interface TinyFishSearchResponse {
  query: string
  results: TinyFishSearchResult[]
  total_results?: number
  page?: number
}

export interface TinyFishFetchedPage {
  url: string
  final_url?: string
  title?: string
  text: string | Record<string, unknown>
}

interface TinyFishFetchResponse {
  results: TinyFishFetchedPage[]
  errors: Array<{ url: string; error: string; status?: number }>
}

export interface TinyFishAutomationRun {
  run_id: string | null
  status: "COMPLETED" | "FAILED"
  started_at?: string | null
  finished_at?: string | null
  num_of_steps?: number | null
  result: Record<string, unknown> | null
  error: { code?: string; message?: string; category?: string } | null
}

export class TinyFishClient {
  constructor(
    private readonly apiKey: string | undefined,
    private readonly searchBaseUrl = "https://api.search.tinyfish.ai",
    private readonly fetchBaseUrl = "https://api.fetch.tinyfish.ai",
    private readonly agentBaseUrl = "https://agent.tinyfish.ai/v1"
  ) {}

  async search(query: string): Promise<TinyFishSearchResult[]> {
    if (!this.apiKey) {
      throw new Error("No API keys added.")
    }

    const response = await fetch(`${this.searchBaseUrl}?query=${encodeURIComponent(query)}&location=US&language=en`, {
      headers: {
        "X-API-Key": this.apiKey
      }
    })

    const payload = await this.parseResponse<TinyFishSearchResponse>(response, "TinyFish search")
    return payload.results ?? []
  }

  async fetchPage(url: string): Promise<TinyFishFetchedPage> {
    const payload = await this.request<TinyFishFetchResponse>(this.fetchBaseUrl, {
      urls: [url],
      format: "markdown",
      links: false,
      image_links: false
    })
    const page = payload.results[0]
    if (!page) {
      const error = payload.errors[0]
      throw new Error(error ? `TinyFish fetch failed for ${error.url}: ${error.error}` : "TinyFish fetch returned no page.")
    }

    return page
  }

  async runAutomation(input: { url: string; goal: string }): Promise<TinyFishAutomationRun> {
    return this.request<TinyFishAutomationRun>(`${this.agentBaseUrl}/automation/run`, {
      url: input.url,
      goal: input.goal,
      browser_profile: "lite",
      api_integration: "argus",
      agent_config: {
        mode: "strict",
        cursor_style: "standard",
        max_steps: 30,
        max_duration_seconds: 180
      },
      capture_config: {
        elements: true,
        snapshots: true,
        screenshots: false,
        recording: false
      }
    })
  }

  private async request<T>(url: string, body: Record<string, unknown>): Promise<T> {
    if (!this.apiKey) {
      throw new Error("No API keys added.")
    }

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "X-API-Key": this.apiKey
      },
      body: JSON.stringify(body)
    })

    return this.parseResponse<T>(response, "TinyFish request")
  }

  private async parseResponse<T>(response: Response, label: string): Promise<T> {
    const text = await response.text()
    if (!response.ok) {
      throw new Error(`${label} failed with ${response.status}: ${text || response.statusText}`)
    }

    return JSON.parse(text) as T
  }
}
