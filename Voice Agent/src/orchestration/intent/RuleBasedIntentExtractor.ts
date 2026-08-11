import type { AutomationIntent, IntentAction } from "~/types/automation"
import type { IntentExtractor } from "~/types/providers"

const WEBSITE_ALIASES: Record<string, string> = {
  amazon: "https://www.amazon.com",
  flipkart: "https://www.flipkart.com",
  youtube: "https://www.youtube.com",
  linkedin: "https://www.linkedin.com",
  google: "https://www.google.com"
}

const WEBSITE_SEARCH_URLS: Record<string, (query: string) => string> = {
  amazon: (query) => `https://www.amazon.com/s?k=${encodeURIComponent(query)}`,
  flipkart: (query) => `https://www.flipkart.com/search?q=${encodeURIComponent(query)}`,
  youtube: (query) => `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`,
  google: (query) => `https://www.google.com/search?q=${encodeURIComponent(query)}`,
  linkedin: (query) => `https://www.linkedin.com/search/results/all/?keywords=${encodeURIComponent(query)}`
}

export class RuleBasedIntentExtractor implements IntentExtractor {
  async extract(command: string): Promise<AutomationIntent> {
    const lower = command.toLowerCase()
    let action = this.detectAction(lower)
    const website = this.detectWebsite(lower)
    const query = this.extractQuery(lower, website)

    // If the user says "open X on Y", they actually mean "search/play X on Y"
    if (action === "open" && query && website) {
      action = website === "youtube" ? "play" : "search"
    }

    // For questions and unknown intents, use the full command as the search query
    const effectiveQuery = (action === "ask" || action === "unknown")
      ? command.trim()
      : query

    return {
      action: action === "unknown" ? "ask" : action,
      ...(website ? { website } : {}),
      ...(effectiveQuery ? { query: effectiveQuery } : {}),
      ...(this.extractTarget(lower) ? { target: this.extractTarget(lower) } : {}),
      rawCommand: command,
      confidence: action === "unknown" ? 0.5 : action === "ask" ? 0.82 : 0.78
    }
  }

  resolveWebsiteUrl(website: string): string {
    return WEBSITE_ALIASES[website.toLowerCase()] ?? `https://${website}`
  }

  resolveWebsiteSearchUrl(website: string, query: string): string {
    const normalizedWebsite = website.toLowerCase()
    return WEBSITE_SEARCH_URLS[normalizedWebsite]?.(query) ?? `${this.resolveWebsiteUrl(website)}/search?q=${encodeURIComponent(query)}`
  }

  resolveGoogleSearchUrl(query: string): string {
    return `https://www.google.com/search?q=${encodeURIComponent(query)}`
  }

  private detectAction(command: string): IntentAction {
    if (/\b(new\s+tab|open\s+(a\s+)?new\s+tab)\b/.test(command)) return "new_tab"
    if (/\b(play|playing|start playing)\b/.test(command)) return "play"
    if (/\b(search|find|look for)\b/.test(command)) return "search"
    if (/\b(open|go to|navigate)\b/.test(command)) return "open"
    if (/\b(click|press|select)\b/.test(command)) return "click"
    if (/\b(type|enter|write)\b/.test(command)) return "type"
    if (/\b(summarize|summary)\b/.test(command)) return "summarize"
    // Question patterns — "what is...", "how to...", "why does...", "meaning of...", etc.
    if (/^(what|why|how|who|when|where|which|whose|whom|is |are |can |do |does |will |would |could |should |shall |did )\b/.test(command)) return "ask"
    if (/\b(meaning of|definition of|define |explain |tell me|what'?s)\b/.test(command)) return "ask"
    return "unknown"
  }

  private detectWebsite(command: string): string | undefined {
    return Object.keys(WEBSITE_ALIASES).find((website) => command.includes(website))
  }

  private extractQuery(command: string, website?: string): string | undefined {
    const patterns = [
      /(?:play|playing|start playing)\s+(.+?)\s+on\s+\w+/,
      /(?:play|playing|start playing)\s+(.+)/,
      /search\s+(.+?)\s+on\s+\w+/,
      /find\s+(.+?)\s+on\s+\w+/,
      /look for\s+(.+?)\s+on\s+\w+/,
      /open\s+(.+?)\s+on\s+\w+/,
      /search\s+(.+)/,
      /find\s+(.+)/
    ]

    for (const pattern of patterns) {
      const match = command.match(pattern)
      if (match?.[1]) {
        return match[1].replace(website ?? "", "").trim()
      }
    }

    return undefined
  }

  private extractTarget(command: string): string | undefined {
    const clickMatch = command.match(/\b(?:click|press|select)\s+(.+)/)
    return clickMatch?.[1]?.trim()
  }
}
