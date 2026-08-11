import type { AutomationAction, ValidationResult } from "./automation"

export interface ResolvedElement {
  strategy: ResolverStrategy
  locator: unknown
  confidence: number
  description: string
}

export type ResolverStrategy =
  | "accessibility"
  | "role"
  | "text"
  | "agentql"
  | "css"
  | "xpath"
  | "vision"

export interface BrowserPage {
  url(): string
  goto(url: string, options?: { waitUntil?: "load" | "domcontentloaded" | "networkidle"; timeout?: number | undefined }): Promise<unknown>
  getByRole(role: string, options?: { name?: string | RegExp | undefined }): unknown
  getByText(text: string | RegExp): unknown
  locator(selector: string): unknown
  waitForTimeout(ms: number): Promise<void>
  keyboard: {
    press(key: string): Promise<void>
  }
}

export interface LocatorLike {
  click(options?: { timeout?: number | undefined }): Promise<void>
  fill(value: string, options?: { timeout?: number | undefined }): Promise<void>
  count?(): Promise<number>
  first?(): LocatorLike
}

export interface ElementResolver {
  resolve(page: BrowserPage, action: AutomationAction): Promise<ResolvedElement>
}

export interface BrowserRuntime {
  getActivePage(): Promise<BrowserPage>
  execute(action: AutomationAction, element?: ResolvedElement): Promise<void>
  observe(): Promise<{ url: string; title?: string }>
}

export interface ActionValidator {
  validate(action: AutomationAction, page: BrowserPage): Promise<ValidationResult>
}
