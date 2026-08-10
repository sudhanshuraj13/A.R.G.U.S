import type { TaskState } from "~/types/automation"
import { createId } from "~/utils/id"

export function createTaskState(goal: string): TaskState {
  return {
    taskId: createId("task"),
    goal,
    completedSteps: [],
    pendingActions: [],
    retries: 0,
    status: "planning",
    errors: [],
    logs: []
  }
}
