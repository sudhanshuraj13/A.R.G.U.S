import type { ExecutionLog } from "~/types/automation"
import { createId } from "./id"

export function createLog(taskId: string, message: string, level: ExecutionLog["level"] = "info", meta?: Record<string, unknown>): ExecutionLog {
  return {
    id: createId("log"),
    taskId,
    level,
    message,
    timestamp: Date.now(),
    ...(meta ? { meta } : {})
  }
}
