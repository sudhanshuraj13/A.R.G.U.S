import type { AutomationAction } from "~/types/automation"
import type { BrowserPage, ElementResolver, ResolvedElement } from "~/types/runtime"

export class VisionResolver implements ElementResolver {
  async resolve(_page: BrowserPage, action: AutomationAction): Promise<ResolvedElement> {
    throw new Error(`Vision fallback is reserved for a future runtime and cannot resolve ${action.description} yet.`)
  }
}
