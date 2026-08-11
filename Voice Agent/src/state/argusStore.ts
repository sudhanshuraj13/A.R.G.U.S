import { create } from "zustand"
import type { ArgusProviderSettings } from "~/settings/ProviderSettings"
import { DEFAULT_PROVIDER_SETTINGS } from "~/settings/ProviderSettings"
import type { ApprovalRequest, ExecutionLog, TaskState, TaskStatus } from "~/types/automation"

interface NotificationItem {
  id: string
  type: "success" | "error" | "info" | "warning"
  message: string
  createdAt: number
}

interface ArgusStore {
  currentTask: TaskState | undefined
  history: TaskState[]
  approvals: ApprovalRequest[]
  notifications: NotificationItem[]
  isListening: boolean
  isWakeWordArmed: boolean
  sidebarOpen: boolean
  settings: ArgusProviderSettings
  setListening(value: boolean): void
  setWakeWordArmed(value: boolean): void
  setSidebarOpen(value: boolean): void
  setSettings(settings: ArgusProviderSettings): void
  setTask(task: TaskState): void
  updateTask(patch: Partial<TaskState>): void
  setStatus(status: TaskStatus): void
  addLog(log: ExecutionLog): void
  addApproval(request: ApprovalRequest): void
  resolveApproval(id: string): void
  notify(notification: Omit<NotificationItem, "id" | "createdAt">): void
  dismissNotification(id: string): void
}

export const useArgusStore = create<ArgusStore>((set) => ({
  currentTask: undefined,
  history: [],
  approvals: [],
  notifications: [],
  isListening: false,
  isWakeWordArmed: true,
  sidebarOpen: false,
  settings: DEFAULT_PROVIDER_SETTINGS,
  setListening: (value) => set({ isListening: value }),
  setWakeWordArmed: (value) => set({ isWakeWordArmed: value }),
  setSidebarOpen: (value) => set({ sidebarOpen: value }),
  setSettings: (settings) => set({ settings }),
  setTask: (task) => set({ currentTask: task }),
  updateTask: (patch) =>
    set((state) => ({
      currentTask: state.currentTask ? { ...state.currentTask, ...patch } : state.currentTask
    })),
  setStatus: (status) =>
    set((state) => ({
      currentTask: state.currentTask ? { ...state.currentTask, status } : state.currentTask
    })),
  addLog: (log) =>
    set((state) => ({
      currentTask: state.currentTask ? { ...state.currentTask, logs: [...state.currentTask.logs, log] } : state.currentTask
    })),
  addApproval: (request) => set((state) => ({ approvals: [...state.approvals, request] })),
  resolveApproval: (id) => set((state) => ({ approvals: state.approvals.filter((approval) => approval.id !== id) })),
  notify: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        {
          ...notification,
          id: `${Date.now()}_${state.notifications.length}`,
          createdAt: Date.now()
        }
      ]
    })),
  dismissNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((notification) => notification.id !== id)
    }))
}))
