import type { TaskState } from "~/types/automation"
import type { IntentExtractor, Planner } from "~/types/providers"
import { createLog } from "~/utils/logging"

/**
 * Browser-safe orchestration facade.
 *
 * The workflow intentionally mirrors the LangGraph node model
 * (shared state in, shared state out) without importing LangGraph into the
 * extension UI bundle. LangGraph can be wired into a Node runtime later without
 * changing callers, while the Chrome popup/content scripts stay lightweight.
 */
export class ArgusGraph {
  constructor(
    private readonly intentExtractor: IntentExtractor,
    private readonly planner: Planner
  ) {}

  async prepare(initialState: TaskState): Promise<TaskState> {
    const withIntent = await this.extractIntent(initialState)
    return this.plan(withIntent)
  }

  private async extractIntent(state: TaskState): Promise<TaskState> {
    const intent = await this.intentExtractor.extract(state.goal)

    return {
      ...state,
      intent,
      status: "planning",
      logs: [...state.logs, createLog(state.taskId, `Intent detected: ${intent.action}`)]
    }
  }

  private async plan(state: TaskState): Promise<TaskState> {
    const pendingActions = await this.planner.plan(state)

    return {
      ...state,
      pendingActions,
      status: pendingActions.length > 0 ? "executing" : "failed",
      errors: pendingActions.length > 0 ? state.errors : [...state.errors, "Planner could not produce actionable steps."],
      logs: [...state.logs, createLog(state.taskId, `Planned ${pendingActions.length} action(s).`)]
    }
  }
}
