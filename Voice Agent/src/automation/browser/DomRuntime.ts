import type { AutomationAction } from "~/types/automation"
import type { BrowserPage, BrowserRuntime, LocatorLike, ResolvedElement } from "~/types/runtime"

export class DomBrowserRuntime implements BrowserRuntime {
  private readonly page = new DomBrowserPage()

  setAgentQLApiKey(_apiKey: string | undefined): void {
    // AgentQL's official element automation SDK works with Playwright pages.
    // The content-script runtime exposes accessibility/text/CSS lookup only.
  }

  async getActivePage(): Promise<BrowserPage> {
    return this.page
  }

  async execute(action: AutomationAction, element?: ResolvedElement): Promise<void> {
    switch (action.kind) {
      case "navigate":
        if (!action.url) throw new Error("Navigate action requires a URL.")
        window.location.assign(action.url)
        await this.page.waitForTimeout(150)
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
        await this.requireLocator(action, element).click({ timeout: action.timeoutMs })
        return
      case "type":
      case "search":
        await this.requireLocator(action, element).fill(action.value ?? "", { timeout: action.timeoutMs })
        await this.page.keyboard.press("Enter")
        return
      case "scroll":
        window.scrollBy({ top: window.innerHeight * 0.85, behavior: "smooth" })
        return
      case "wait":
        await this.page.waitForTimeout(action.timeoutMs ?? 1_000)
        return
      case "summarize":
      case "extract":
        return
      default:
        throw new Error(`Unsupported action kind: ${action.kind}`)
    }
  }

  async observe(): Promise<{ url: string; title?: string }> {
    return { url: window.location.href, title: document.title }
  }

  private requireLocator(action: AutomationAction, element?: ResolvedElement): LocatorLike {
    if (!element?.locator) {
      throw new Error(`${action.kind} requires a resolved element.`)
    }

    return element.locator as LocatorLike
  }
}

class DomBrowserPage implements BrowserPage {
  keyboard = {
    press: async (key: string) => {
      if (key === "Enter") {
        const active = document.activeElement
        active?.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }))
        active?.dispatchEvent(new KeyboardEvent("keyup", { key, bubbles: true }))
        active?.closest("form")?.requestSubmit()
      }
    }
  }

  url(): string {
    return window.location.href
  }

  async goto(url: string): Promise<unknown> {
    window.location.assign(url)
    await this.waitForTimeout(150)
    return undefined
  }

  getByRole(role: string, options?: { name?: string | RegExp | undefined }): LocatorLike {
    const candidates = getRoleCandidates(role)
    const name = options?.name
    const named = name ? candidates.filter((element) => matchesName(element, name)) : candidates
    return new DomLocator(named.length > 0 ? named : candidates)
  }

  getByText(text: string | RegExp): LocatorLike {
    const elements = Array.from(document.querySelectorAll<HTMLElement>("button, a, input, textarea, select, [role], [aria-label], [title]"))
    return new DomLocator(elements.filter((element) => matchesText(getElementName(element), text)))
  }

  locator(selector: string): LocatorLike {
    return new DomLocator(Array.from(document.querySelectorAll<HTMLElement>(selector)))
  }

  async waitForTimeout(ms: number): Promise<void> {
    await new Promise((resolve) => window.setTimeout(resolve, ms))
  }
}

class DomLocator implements LocatorLike {
  constructor(private readonly elements: HTMLElement[]) {}

  async click(): Promise<void> {
    const element = this.firstElement()
    element.focus()
    element.click()
  }

  async fill(value: string): Promise<void> {
    const element = this.firstElement()
    if (!isFillable(element)) {
      throw new Error("Resolved element cannot be filled.")
    }

    element.focus()
    element.value = value
    element.dispatchEvent(new InputEvent("input", { bubbles: true, data: value, inputType: "insertText" }))
    element.dispatchEvent(new Event("change", { bubbles: true }))
  }

  async count(): Promise<number> {
    return this.elements.length
  }

  first(): LocatorLike {
    return new DomLocator(this.elements.slice(0, 1))
  }

  private firstElement(): HTMLElement {
    const element = this.elements[0]
    if (!element) {
      throw new Error("No matching element found on this page.")
    }

    return element
  }
}

function getRoleCandidates(role: string): HTMLElement[] {
  const selectors: Record<string, string> = {
    button: "button, input[type='button'], input[type='submit'], input[type='reset'], [role='button']",
    textbox: "input:not([type]), input[type='text'], input[type='search'], input[type='email'], input[type='password'], textarea, [role='textbox']",
    link: "a[href], [role='link']"
  }

  return Array.from(document.querySelectorAll<HTMLElement>(selectors[role] ?? `[role='${CSS.escape(role)}']`))
}

function matchesName(element: HTMLElement, name: string | RegExp): boolean {
  return matchesText(getElementName(element), name)
}

function matchesText(value: string, matcher: string | RegExp): boolean {
  return typeof matcher === "string" ? value.toLowerCase().includes(matcher.toLowerCase()) : matcher.test(value)
}

function getElementName(element: HTMLElement): string {
  return [
    element.getAttribute("aria-label"),
    element.getAttribute("title"),
    element.textContent,
    isFillable(element) ? element.placeholder : undefined,
    isFillable(element) ? element.name : undefined
  ]
    .filter(Boolean)
    .join(" ")
    .trim()
}

function isFillable(element: HTMLElement): element is HTMLInputElement | HTMLTextAreaElement {
  return element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement
}
