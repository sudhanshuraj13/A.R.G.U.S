import type { AutomationAction } from "~/types/automation"
import type { BrowserPage, ElementResolver, ResolvedElement } from "~/types/runtime"
import { AccessibilityResolver } from "./AccessibilityResolver"
import { AgentQLResolver } from "./AgentQLResolver"

export class CascadingElementResolver implements ElementResolver {
  constructor(
    private readonly resolvers: ElementResolver[] = [new AccessibilityResolver(), new AgentQLResolver()]
  ) {}

  async resolve(page: BrowserPage, action: AutomationAction): Promise<ResolvedElement> {
    const errors: string[] = []

    for (const resolver of this.resolvers) {
      try {
        return await resolver.resolve(page, action)
      } catch (error) {
        errors.push(error instanceof Error ? error.message : String(error))
      }
    }

    throw new Error(`Unable to resolve element for "${action.description}". ${errors.join(" ")}`)
  }
}
