import type { AutomationAction, RiskLevel } from "~/types/automation"

const CONFIRMATION_TERMS = [
  "purchase",
  "buy",
  "checkout",
  "submit",
  "send",
  "post",
  "delete",
  "remove",
  "apply",
  "unsubscribe"
]

const BLOCKED_TERMS = [
  "otp",
  "one time password",
  "password manager",
  "bank transfer",
  "wire transfer",
  "security settings",
  "two factor",
  "2fa"
]

export class RiskClassifier {
  classify(action: AutomationAction): RiskLevel {
    const haystack = `${action.kind} ${action.description} ${action.target ?? ""} ${action.value ?? ""}`.toLowerCase()

    if (BLOCKED_TERMS.some((term) => haystack.includes(term))) {
      return "blocked"
    }

    if (CONFIRMATION_TERMS.some((term) => haystack.includes(term))) {
      return "confirmation_required"
    }

    return "safe"
  }
}
