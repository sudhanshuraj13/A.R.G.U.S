import type { AutomationAction, ValidationResult } from "~/types/automation"
import type { ActionValidator as ActionValidatorContract, BrowserPage } from "~/types/runtime"

export class BasicActionValidator implements ActionValidatorContract {
  async validate(action: AutomationAction, page: BrowserPage): Promise<ValidationResult> {
    if (action.kind === "navigate") {
      const url = page.url()
      return {
        ok: Boolean(url && url !== "about:blank"),
        evidence: url,
        ...(url === "about:blank" ? { reason: "Navigation did not leave blank page." } : {})
      }
    }

    return { ok: true, evidence: `${action.kind} completed` }
  }
}
