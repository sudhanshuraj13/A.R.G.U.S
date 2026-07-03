import type { TaskState } from "~/types/automation"

export interface UserPreference {
  key: string
  value: string
  updatedAt: number
}

export class TaskMemory {
  private readonly tasks: TaskState[] = []
  private readonly preferences = new Map<string, UserPreference>()

  rememberTask(task: TaskState): void {
    this.tasks.unshift(task)
    this.tasks.splice(25)
  }

  listRecentTasks(): TaskState[] {
    return [...this.tasks]
  }

  setPreference(key: string, value: string): void {
    this.preferences.set(key, { key, value, updatedAt: Date.now() })
  }

  getPreference(key: string): UserPreference | undefined {
    return this.preferences.get(key)
  }
}
