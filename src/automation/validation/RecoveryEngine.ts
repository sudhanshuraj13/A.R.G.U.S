import type { AutomationAction, TaskState } from "~/types/automation"
import { createLog } from "~/utils/logging"

export class RecoveryEngine {
  constructor(private readonly maxRetries = 2) {}

  async recover(state: TaskState, failedAction: AutomationAction, error: unknown): Promise<TaskState> {
    const message = error instanceof Error ? error.message : String(error)
    const retries = state.retries + 1

    if (retries > this.maxRetries) {
      return {
        ...state,
        status: "failed",
        errors: [...state.errors, message],
        logs: [...state.logs, createLog(state.taskId, `Failed after retries: ${message}`, "error")]
      }
    }

    return {
      ...state,
      status: "recovering",
      retries,
      pendingActions: [failedAction, ...state.pendingActions.filter((action) => action.id !== failedAction.id)],
      logs: [...state.logs, createLog(state.taskId, `Retrying ${failedAction.description}: ${message}`, "warn")]
    }
  }
}
