import type { AutomationAction } from "~/types/automation"
import type { BrowserPage, BrowserRuntime, LocatorLike, ResolvedElement } from "~/types/runtime"

export class PlaywrightRuntime implements BrowserRuntime {
  constructor(private readonly pageProvider: () => Promise<BrowserPage>) {}

  async getActivePage(): Promise<BrowserPage> {
    return this.pageProvider()
  }

  async execute(action: AutomationAction, element?: ResolvedElement): Promise<void> {
    const page = await this.getActivePage()
    const timeout = action.timeoutMs ?? 10_000

    switch (action.kind) {
      case "navigate":
        if (!action.url) throw new Error("Navigate action requires a URL.")
        await page.goto(action.url, { waitUntil: "domcontentloaded", timeout })
        return
      case "new_tab": {
        const response = await chrome.runtime.sendMessage({
          type: "ARGUS_NEW_TAB",
          url: action.url
        })
        if (response && !response.ok) {
          throw new Error(response.error ?? "Failed to open new tab.")
        }
        return
      }
      case "click":
        await this.requireLocator(action, element).click({ timeout })
        return
      case "type":
      case "search":
        await this.requireLocator(action, element).fill(action.value ?? "", { timeout })
        await page.keyboard.press("Enter")
        return
      case "scroll":
        await page.keyboard.press("PageDown")
        return
      case "wait":
        await page.waitForTimeout(action.timeoutMs ?? 1_000)
        return
      case "summarize":
      case "extract":
        return
      default:
        throw new Error(`Unsupported action kind: ${action.kind}`)
    }
  }

  async observe(): Promise<{ url: string }> {
    const page = await this.getActivePage()
    return { url: page.url() }
  }

  private requireLocator(action: AutomationAction, element?: ResolvedElement): LocatorLike {
    if (!element?.locator) {
      throw new Error(`${action.kind} requires a resolved element.`)
    }

    return element.locator as LocatorLike
  }
}
