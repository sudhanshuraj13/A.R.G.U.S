import type { ApprovalRequest, AutomationAction } from "~/types/automation"
import { createId } from "~/utils/id"
import { RiskClassifier } from "./RiskClassifier"

export type PermissionDecision =
  | { allowed: true; approval?: undefined }
  | { allowed: false; blocked: true; reason: string; approval?: undefined }
  | { allowed: false; blocked?: false; approval: ApprovalRequest; reason: string }

export class PermissionSystem {
  constructor(private readonly riskClassifier = new RiskClassifier()) {}

  evaluate(taskId: string, action: AutomationAction): PermissionDecision {
    const risk = this.riskClassifier.classify(action)

    if (risk === "blocked") {
      return {
        allowed: false,
        blocked: true,
        reason: "ARGUS blocks this action by policy because it can expose credentials, money movement, or security settings."
      }
    }

    if (risk === "confirmation_required") {
      return {
        allowed: false,
        reason: "This action changes external state and requires human approval.",
        approval: {
          id: createId("approval"),
          taskId,
          action: { ...action, risk },
          risk,
          reason: "This action changes external state and requires human approval.",
          createdAt: Date.now()
        }
      }
    }

    return { allowed: true }
  }
}
