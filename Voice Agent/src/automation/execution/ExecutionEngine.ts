import type { ApprovalRequest, AutomationAction, TaskState } from "~/types/automation"
import type { ActionValidator, BrowserRuntime, ElementResolver } from "~/types/runtime"
import { createLog } from "~/utils/logging"
import { PermissionSystem } from "~/safety/PermissionSystem"
import { RecoveryEngine } from "../validation/RecoveryEngine"

export interface ExecutionEvents {
  onTaskUpdate(state: TaskState): void
  onApprovalRequired(request: ApprovalRequest): void
}

export class ExecutionEngine {
  constructor(
    private readonly runtime: BrowserRuntime,
    private readonly resolver: ElementResolver,
    private readonly validator: ActionValidator,
    private readonly permissions = new PermissionSystem(),
    private readonly recovery = new RecoveryEngine()
  ) {}

  async run(state: TaskState, events: ExecutionEvents): Promise<TaskState> {
    let nextState: TaskState = { ...state, status: "executing" }
    events.onTaskUpdate(nextState)

    while (nextState.pendingActions.length > 0) {
      const [action, ...remaining] = nextState.pendingActions
      if (!action) break

      const decision = this.permissions.evaluate(nextState.taskId, action)
      if (!decision.allowed) {
        if (decision.approval) {
          events.onApprovalRequired(decision.approval)
          return {
            ...nextState,
            status: "waiting_approval",
            currentStep: action,
            pendingActions: [action, ...remaining],
            logs: [...nextState.logs, createLog(nextState.taskId, decision.reason, "warn")]
          }
        }

        return {
          ...nextState,
          status: "blocked",
          currentStep: action,
          errors: [...nextState.errors, decision.reason],
          logs: [...nextState.logs, createLog(nextState.taskId, decision.reason, "error")]
        }
      }

      try {
        const page = await this.runtime.getActivePage()
        const element = action.kind === "navigate" || action.kind === "new_tab" || action.kind === "wait" ? undefined : await this.resolver.resolve(page, action)
        await this.runtime.execute(action, element)
        const validation = await this.validator.validate(action, page)

        if (!validation.ok) {
          throw new Error(validation.reason ?? "Action validation failed.")
        }

        nextState = {
          ...nextState,
          currentPage: page.url(),
          currentStep: action,
          completedSteps: [...nextState.completedSteps, action],
          pendingActions: remaining,
          validation,
          logs: [...nextState.logs, createLog(nextState.taskId, `Completed: ${action.description}`)]
        }
        events.onTaskUpdate(nextState)
      } catch (error) {
        nextState = await this.recovery.recover(nextState, action, error)
        events.onTaskUpdate(nextState)
        if (nextState.status === "failed") return nextState
      }
    }

    return {
      ...nextState,
      status: "completed",
      currentStep: undefined
    }
  }
}
