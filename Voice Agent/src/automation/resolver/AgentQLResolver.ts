import type { AutomationAction } from "~/types/automation"
import type { BrowserPage, ElementResolver, LocatorLike, ResolvedElement } from "~/types/runtime"

interface AgentQLPage {
  queryElements(query: string): Promise<Record<string, LocatorLike>>
}

export class AgentQLResolver implements ElementResolver {
  async resolve(page: BrowserPage, action: AutomationAction): Promise<ResolvedElement> {
    const target = action.target ?? action.description
    const agentqlPage = page as BrowserPage & Partial<AgentQLPage>

    if (typeof agentqlPage.queryElements !== "function") {
      throw new Error("AgentQL is not attached to this Playwright page.")
    }

    const result = await agentqlPage.queryElements(`{ target_element(description: "${target}") }`)
    const locator = result["target_element"]
    if (!locator) {
      throw new Error(`AgentQL could not resolve ${target}.`)
    }

    return {
      strategy: "agentql",
      locator,
      confidence: 0.74,
      description: `Resolved ${target} through AgentQL semantic query`
    }
  }
}
