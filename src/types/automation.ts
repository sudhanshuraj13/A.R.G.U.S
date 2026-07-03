export type TaskStatus =
  | "idle"
  | "planning"
  | "waiting_approval"
  | "executing"
  | "validating"
  | "recovering"
  | "completed"
  | "failed"
  | "blocked"

export type IntentAction =
  | "search"
  | "play"
  | "open"
  | "new_tab"
  | "ask"
  | "click"
  | "type"
  | "summarize"
  | "navigate"
  | "extract"
  | "unknown"

export type RiskLevel = "safe" | "confirmation_required" | "blocked"

export interface AutomationIntent {
  action: IntentAction
  website?: string | undefined
  query?: string | undefined
  target?: string | undefined
  value?: string | undefined
  rawCommand: string
  confidence: number
}

export type ActionKind =
  | "navigate"
  | "new_tab"
  | "search"
  | "click"
  | "type"
  | "scroll"
  | "wait"
  | "summarize"
  | "extract"

export interface AutomationAction {
  id: string
  kind: ActionKind
  description: string
  target?: string | undefined
  value?: string | undefined
  url?: string | undefined
  timeoutMs?: number | undefined
  risk?: RiskLevel | undefined
}

export interface ExecutionLog {
  id: string
  taskId: string
  level: "info" | "warn" | "error"
  message: string
  timestamp: number
  meta?: Record<string, unknown> | undefined
}

export interface ValidationResult {
  ok: boolean
  reason?: string | undefined
  evidence?: string | undefined
}

export interface TaskState {
  taskId: string
  goal: string
  intent?: AutomationIntent | undefined
  currentPage?: string | undefined
  currentStep?: AutomationAction | undefined
  completedSteps: AutomationAction[]
  pendingActions: AutomationAction[]
  retries: number
  validation?: ValidationResult | undefined
  status: TaskStatus
  errors: string[]
  logs: ExecutionLog[]
}

export interface ApprovalRequest {
  id: string
  taskId: string
  action: AutomationAction
  risk: RiskLevel
  reason: string
  createdAt: number
}
