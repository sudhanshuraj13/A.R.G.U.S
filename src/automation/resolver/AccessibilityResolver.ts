import type { AutomationAction } from "~/types/automation"
import type { BrowserPage, ElementResolver, LocatorLike, ResolvedElement } from "~/types/runtime"

const ROLE_HINTS: Array<{ pattern: RegExp; role: string }> = [
  { pattern: /button|checkout|submit|search|login|sign in/i, role: "button" },
  { pattern: /input|field|search|email|username|password/i, role: "textbox" },
  { pattern: /link|open/i, role: "link" }
]

export class AccessibilityResolver implements ElementResolver {
  async resolve(page: BrowserPage, action: AutomationAction): Promise<ResolvedElement> {
    const target = action.target ?? action.description
    if (/first youtube video/i.test(target)) {
      const locator = page.locator("ytd-video-renderer a#video-title, a#video-title, a[href^='/watch']") as LocatorLike
      return {
        strategy: "css",
        locator: locator.first?.() ?? locator,
        confidence: 0.82,
        description: "Resolved the first YouTube video result"
      }
    }

    const role = ROLE_HINTS.find((hint) => hint.pattern.test(target))?.role

    if (role) {
      const locator = page.getByRole(role, { name: new RegExp(target.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i") }) as LocatorLike
      return {
        strategy: "role",
        locator,
        confidence: 0.84,
        description: `Resolved ${target} through accessibility role ${role}`
      }
    }

    return {
      strategy: "text",
      locator: page.getByText(new RegExp(target.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i")) as LocatorLike,
      confidence: 0.68,
      description: `Resolved ${target} through visible text`
    }
  }
}
