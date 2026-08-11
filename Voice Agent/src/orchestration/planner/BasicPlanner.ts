import type { AutomationAction, TaskState } from "~/types/automation"
import type { Planner } from "~/types/providers"
import { createId } from "~/utils/id"
import { RuleBasedIntentExtractor } from "../intent/RuleBasedIntentExtractor"

export class BasicPlanner implements Planner {
  private readonly intentTools = new RuleBasedIntentExtractor()

  async plan(state: TaskState): Promise<AutomationAction[]> {
    const intent = state.intent
    if (!intent) {
      return []
    }

    if (intent.action === "search" && intent.website && intent.query) {
      return [
        {
          id: createId("action"),
          kind: "navigate",
          description: `Search ${intent.website} for ${intent.query}`,
          url: this.intentTools.resolveWebsiteSearchUrl(intent.website, intent.query)
        }
      ]
    }



    if (intent.action === "open" && intent.website) {
      return [
        {
          id: createId("action"),
          kind: "navigate",
          description: `Open ${intent.website}`,
          url: this.intentTools.resolveWebsiteUrl(intent.website)
        }
      ]
    }

    if (intent.action === "click" && intent.target) {
      return [
        {
          id: createId("action"),
          kind: "click",
          description: `Click ${intent.target}`,
          target: intent.target
        }
      ]
    }

    if (intent.action === "summarize") {
      return [
        {
          id: createId("action"),
          kind: "summarize",
          description: "Summarize the current webpage"
        }
      ]
    }

    if (intent.action === "new_tab") {
      const url = intent.website ? this.intentTools.resolveWebsiteUrl(intent.website) : undefined
      return [
        {
          id: createId("action"),
          kind: "new_tab",
          description: url ? `Open ${intent.website} in a new tab` : "Open a new tab",
          ...(url ? { url } : {})
        }
      ]
    }

    // Questions and general queries → Google search in a new tab
    if (intent.action === "ask" && intent.query) {
      return [
        {
          id: createId("action"),
          kind: "new_tab",
          description: `Search Google for "${intent.query}"`,
          url: this.intentTools.resolveGoogleSearchUrl(intent.query)
        }
      ]
    }

    return []
  }
}
