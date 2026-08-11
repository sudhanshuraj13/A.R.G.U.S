import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from "react"
import { ArgusController } from "~/orchestration/ArgusController"
import { ProviderSettingsStore } from "~/settings/ProviderSettings"
import { requireApiKeys } from "~/settings/requireApiKeys"
import { useArgusStore } from "~/state/argusStore"
import type { TaskState } from "~/types/automation"
import { SettingsPanel } from "~/ui/settings/SettingsPanel"
import "../styles.css"

/**
 * ARGUS Side Panel — the primary interface that works on EVERY tab,
 * including chrome://newtab where content scripts can't inject.
 */
export function SidePanelApp() {
  const store = useArgusStore()
  const controller = useMemo(() => new ArgusController(), [])
  const settingsStore = useMemo(() => new ProviderSettingsStore(), [])
  const [view, setView] = useState<"main" | "settings">("main")
  const [commandInput, setCommandInput] = useState("")
  const logsEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    void settingsStore.load().then(store.setSettings)
  }, [settingsStore, store.setSettings])

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [store.currentTask?.logs.length])

  const submitCommand = async (command: string) => {
    if (!command.trim()) return

    try {
      const settings = await settingsStore.load()
      store.setSettings(settings)
      requireApiKeys(settings)

      store.setStatus("planning")
      const task = await controller.prepareCommand(command, settings)
      store.setTask(task)
      store.notify({
        type: task.status === "failed" ? "error" : "info",
        message: `Prepared ${task.pendingActions.length} action(s).`
      })

      if (task.pendingActions.length > 0) {
        // Send command to the content script in the active tab for execution
        try {
          await chrome.runtime.sendMessage({
            type: "ARGUS_EXECUTE_ON_TAB",
            command
          })
        } catch {
          store.notify({
            type: "warning",
            message: "Could not reach the active tab. Content script may not be loaded on this page."
          })
        }
      }
    } catch (error) {
      store.notify({
        type: "error",
        message: error instanceof Error ? error.message : "ARGUS could not prepare the command."
      })
    }
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const command = commandInput.trim()
    if (command) {
      void submitCommand(command)
      setCommandInput("")
    }
  }

  const statusInfo = getStatusInfo(store.currentTask)

  return (
    <div style={rootStyle}>
      {/* ─── Header ────────────────────────────────────────────── */}
      <header style={headerStyle}>
        <div style={headerLeftStyle}>
          <div style={logoStyle}>
            <span style={logoLetterStyle}>A</span>
            <span style={logoDotStyle(store.currentTask?.status)} />
          </div>
          <div>
            <h1 style={titleStyle}>ARGUS</h1>
            <p style={subtitleStyle}>{statusInfo.label}</p>
          </div>
        </div>
        <button
          type="button"
          style={headerBtnStyle}
          onClick={() => setView(view === "settings" ? "main" : "settings")}
          title={view === "settings" ? "Back" : "Settings"}
        >
          {view === "settings" ? "←" : "⚙"}
        </button>
      </header>

      {/* ─── Status Bar ────────────────────────────────────────── */}
      <div style={statusBarStyle(statusInfo.color)} />

      {view === "settings" ? (
        <div style={scrollAreaStyle}>
          <SettingsPanel />
        </div>
      ) : (
        <>
          {/* ─── Command Input ───────────────────────────────────── */}
          <form style={commandFormStyle} onSubmit={handleSubmit}>
            <div style={inputWrapperStyle}>
              <input
                id="argus-sidepanel-command"
                type="text"
                value={commandInput}
                onChange={(event) => setCommandInput(event.target.value)}
                placeholder="Try: open new tab, search headphones on Amazon..."
                style={inputStyle}
                autoComplete="off"
              />
              <button type="submit" style={sendBtnStyle} disabled={!commandInput.trim()}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>
          </form>

          {/* ─── Quick Actions ───────────────────────────────────── */}
          <div style={quickActionsStyle}>
            {QUICK_ACTIONS.map((qa) => (
              <button
                key={qa.label}
                type="button"
                style={chipStyle}
                onClick={() => {
                  setCommandInput(qa.command)
                  void submitCommand(qa.command)
                }}
              >
                <span style={chipIconStyle}>{qa.icon}</span>
                {qa.label}
              </button>
            ))}
          </div>

          {/* ─── Scrollable Content ──────────────────────────────── */}
          <div style={scrollAreaStyle}>
            {/* Current Task */}
            {store.currentTask ? (
              <section style={sectionStyle}>
                <h2 style={sectionTitleStyle}>
                  <span style={sectionIconStyle}>🎯</span> Current Task
                </h2>
                <p style={goalTextStyle}>{store.currentTask.goal}</p>

                {/* Pending Actions */}
                {store.currentTask.pendingActions.length > 0 && (
                  <div style={stepsContainerStyle}>
                    <p style={stepsLabelStyle}>Pending</p>
                    {store.currentTask.pendingActions.map((action, index) => (
                      <div key={action.id} style={stepCardStyle("pending")}>
                        <span style={stepNumberStyle("pending")}>{index + 1}</span>
                        <span style={stepTextStyle}>{action.description}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Completed Steps */}
                {store.currentTask.completedSteps.length > 0 && (
                  <div style={stepsContainerStyle}>
                    <p style={stepsLabelStyle}>Completed</p>
                    {store.currentTask.completedSteps.map((action, index) => (
                      <div key={action.id} style={stepCardStyle("done")}>
                        <span style={stepNumberStyle("done")}>✓</span>
                        <span style={stepTextStyle}>{action.description}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            ) : (
              <section style={emptyStateStyle}>
                <div style={emptyIconStyle}>🛡️</div>
                <p style={emptyTitleStyle}>ARGUS is ready</p>
                <p style={emptyDescStyle}>
                  Type a command or use a quick action above.
                  Works on every tab — even this one.
                </p>
              </section>
            )}

            {/* Logs */}
            {store.currentTask && store.currentTask.logs.length > 0 && (
              <section style={sectionStyle}>
                <h2 style={sectionTitleStyle}>
                  <span style={sectionIconStyle}>📋</span> Activity Log
                </h2>
                <div style={logsContainerStyle}>
                  {store.currentTask.logs.map((log) => (
                    <div key={log.id} style={logEntryStyle(log.level)}>
                      <span style={logLevelStyle(log.level)}>{log.level}</span>
                      <span style={logMsgStyle}>{log.message}</span>
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </div>
              </section>
            )}

            {/* Notifications */}
            {store.notifications.length > 0 && (
              <section style={sectionStyle}>
                <h2 style={sectionTitleStyle}>
                  <span style={sectionIconStyle}>🔔</span> Notifications
                </h2>
                {store.notifications.map((notification) => (
                  <button
                    key={notification.id}
                    type="button"
                    style={notificationCardStyle(notification.type)}
                    onClick={() => store.dismissNotification(notification.id)}
                  >
                    <span style={notifTypeStyle}>{notification.type}</span>
                    <span style={notifMsgStyle}>{notification.message}</span>
                  </button>
                ))}
              </section>
            )}
          </div>
        </>
      )}
    </div>
  )
}

// ─── Quick actions ──────────────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { icon: "➕", label: "New Tab", command: "open new tab" },
  { icon: "🔍", label: "Google", command: "open google" },
  { icon: "▶️", label: "YouTube", command: "open youtube" },
  { icon: "🛒", label: "Amazon", command: "open amazon" }
]

// ─── Status helpers ─────────────────────────────────────────────────────────
function getStatusInfo(task: TaskState | undefined): { label: string; color: string } {
  if (!task) return { label: "Ready — listening for commands", color: "#34D399" }
  switch (task.status) {
    case "planning": return { label: "Planning actions…", color: "#60A5FA" }
    case "executing": return { label: "Executing…", color: "#F59E0B" }
    case "waiting_approval": return { label: "Waiting for approval", color: "#EF4444" }
    case "completed": return { label: "Task completed", color: "#34D399" }
    case "failed": return { label: "Task failed", color: "#EF4444" }
    case "blocked": return { label: "Action blocked", color: "#EF4444" }
    default: return { label: task.status, color: "#9CA3AF" }
  }
}

// ─── Styles ─────────────────────────────────────────────────────────────────
const rootStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  height: "100vh",
  background: "linear-gradient(180deg, #0F172A 0%, #111827 100%)",
  color: "#F3F4F6",
  fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  overflow: "hidden"
}

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "14px 16px",
  background: "rgba(15, 23, 42, 0.8)",
  backdropFilter: "blur(12px)",
  borderBottom: "1px solid rgba(255, 255, 255, 0.06)"
}

const headerLeftStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 12
}

const logoStyle: CSSProperties = {
  position: "relative",
  display: "grid",
  placeItems: "center",
  width: 38,
  height: 38,
  borderRadius: 10,
  background: "linear-gradient(135deg, #0F766E, #14B8A6)",
  boxShadow: "0 4px 20px rgba(20, 184, 166, 0.3)"
}

const logoLetterStyle: CSSProperties = {
  fontSize: 18,
  fontWeight: 800,
  color: "#FFFFFF",
  lineHeight: 1
}

function logoDotStyle(status?: string): CSSProperties {
  const color = status === "executing" ? "#F59E0B" : status === "failed" ? "#EF4444" : "#34D399"
  return {
    position: "absolute",
    right: -2,
    bottom: -2,
    width: 10,
    height: 10,
    borderRadius: 999,
    background: color,
    border: "2px solid #0F172A",
    boxShadow: `0 0 8px ${color}`
  }
}

const titleStyle: CSSProperties = {
  fontSize: 15,
  fontWeight: 700,
  color: "#F9FAFB",
  lineHeight: 1.2,
  margin: 0
}

const subtitleStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 500,
  color: "#9CA3AF",
  lineHeight: 1.2,
  margin: 0
}

const headerBtnStyle: CSSProperties = {
  display: "grid",
  placeItems: "center",
  width: 32,
  height: 32,
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  background: "rgba(255, 255, 255, 0.04)",
  color: "#9CA3AF",
  fontSize: 16,
  cursor: "pointer"
}

function statusBarStyle(color: string): CSSProperties {
  return {
    height: 2,
    background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
    opacity: 0.7
  }
}

const commandFormStyle: CSSProperties = {
  padding: "12px 16px 8px"
}

const inputWrapperStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 0,
  borderRadius: 12,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  background: "rgba(255, 255, 255, 0.04)",
  overflow: "hidden",
  transition: "border-color 0.2s"
}

const inputStyle: CSSProperties = {
  flex: 1,
  minWidth: 0,
  padding: "11px 14px",
  background: "transparent",
  border: "none",
  outline: "none",
  color: "#F3F4F6",
  fontSize: 13,
  fontFamily: "inherit"
}

const sendBtnStyle: CSSProperties = {
  display: "grid",
  placeItems: "center",
  width: 40,
  height: 40,
  background: "linear-gradient(135deg, #0F766E, #14B8A6)",
  border: "none",
  color: "#FFFFFF",
  cursor: "pointer",
  flexShrink: 0,
  borderRadius: "0 11px 11px 0"
}

const quickActionsStyle: CSSProperties = {
  display: "flex",
  gap: 6,
  padding: "4px 16px 12px",
  flexWrap: "wrap"
}

const chipStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  padding: "5px 10px",
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.06)",
  background: "rgba(255, 255, 255, 0.03)",
  color: "#D1D5DB",
  fontSize: 11,
  fontWeight: 500,
  cursor: "pointer",
  fontFamily: "inherit",
  transition: "background 0.15s, border-color 0.15s"
}

const chipIconStyle: CSSProperties = { fontSize: 12 }

const scrollAreaStyle: CSSProperties = {
  flex: 1,
  overflowY: "auto",
  overflowX: "hidden",
  padding: "0 16px 16px"
}

const sectionStyle: CSSProperties = {
  marginTop: 14,
  padding: 14,
  borderRadius: 12,
  border: "1px solid rgba(255, 255, 255, 0.05)",
  background: "rgba(255, 255, 255, 0.02)"
}

const sectionTitleStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  fontSize: 12,
  fontWeight: 700,
  color: "#D1D5DB",
  textTransform: "uppercase",
  letterSpacing: 0.5,
  margin: 0
}

const sectionIconStyle: CSSProperties = { fontSize: 13 }

const goalTextStyle: CSSProperties = {
  marginTop: 8,
  fontSize: 13,
  color: "#E5E7EB",
  lineHeight: 1.45
}

const stepsContainerStyle: CSSProperties = { marginTop: 10 }

const stepsLabelStyle: CSSProperties = {
  fontSize: 10,
  fontWeight: 600,
  color: "#6B7280",
  textTransform: "uppercase",
  letterSpacing: 0.8,
  marginBottom: 6
}

function stepCardStyle(kind: "pending" | "done"): CSSProperties {
  return {
    display: "flex",
    alignItems: "flex-start",
    gap: 8,
    padding: "8px 10px",
    borderRadius: 8,
    marginBottom: 4,
    background: kind === "done" ? "rgba(16, 185, 129, 0.08)" : "rgba(255, 255, 255, 0.03)",
    border: `1px solid ${kind === "done" ? "rgba(16, 185, 129, 0.15)" : "rgba(255, 255, 255, 0.04)"}`
  }
}

function stepNumberStyle(kind: "pending" | "done"): CSSProperties {
  return {
    display: "grid",
    placeItems: "center",
    width: 20,
    height: 20,
    borderRadius: 6,
    background: kind === "done" ? "rgba(16, 185, 129, 0.2)" : "rgba(255, 255, 255, 0.06)",
    color: kind === "done" ? "#34D399" : "#9CA3AF",
    fontSize: 10,
    fontWeight: 700,
    flexShrink: 0
  }
}

const stepTextStyle: CSSProperties = {
  fontSize: 12,
  color: "#D1D5DB",
  lineHeight: 1.4,
  paddingTop: 2
}

// ─── Empty state ────────────────────────────────────────────────────────────
const emptyStateStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  textAlign: "center",
  padding: "40px 24px",
  gap: 8
}

const emptyIconStyle: CSSProperties = { fontSize: 36, marginBottom: 4 }

const emptyTitleStyle: CSSProperties = {
  fontSize: 16,
  fontWeight: 700,
  color: "#F3F4F6",
  margin: 0
}

const emptyDescStyle: CSSProperties = {
  fontSize: 12,
  color: "#6B7280",
  lineHeight: 1.5,
  maxWidth: 240,
  margin: 0
}

// ─── Logs ───────────────────────────────────────────────────────────────────
const logsContainerStyle: CSSProperties = {
  marginTop: 8,
  maxHeight: 200,
  overflowY: "auto"
}

function logEntryStyle(level: string): CSSProperties {
  return {
    display: "flex",
    gap: 6,
    padding: "4px 0",
    borderBottom: "1px solid rgba(255, 255, 255, 0.03)",
    alignItems: "baseline"
  }
}

function logLevelStyle(level: string): CSSProperties {
  const colors: Record<string, string> = {
    info: "#60A5FA",
    warn: "#F59E0B",
    error: "#EF4444"
  }
  return {
    fontSize: 9,
    fontWeight: 700,
    textTransform: "uppercase",
    color: colors[level] ?? "#9CA3AF",
    flexShrink: 0
  }
}

const logMsgStyle: CSSProperties = {
  fontSize: 11,
  color: "#9CA3AF",
  lineHeight: 1.4
}

// ─── Notifications ──────────────────────────────────────────────────────────
function notificationCardStyle(type: string): CSSProperties {
  const borderColors: Record<string, string> = {
    success: "rgba(16, 185, 129, 0.3)",
    error: "rgba(239, 68, 68, 0.3)",
    warning: "rgba(245, 158, 11, 0.3)",
    info: "rgba(96, 165, 250, 0.3)"
  }
  return {
    display: "block",
    width: "100%",
    textAlign: "left",
    padding: "10px 12px",
    borderRadius: 8,
    border: `1px solid ${borderColors[type] ?? "rgba(255,255,255,0.06)"}`,
    background: "rgba(255, 255, 255, 0.02)",
    cursor: "pointer",
    marginTop: 6,
    fontFamily: "inherit"
  }
}

const notifTypeStyle: CSSProperties = {
  display: "block",
  fontSize: 10,
  fontWeight: 700,
  textTransform: "uppercase",
  color: "#9CA3AF",
  marginBottom: 2
}

const notifMsgStyle: CSSProperties = {
  display: "block",
  fontSize: 12,
  color: "#D1D5DB",
  lineHeight: 1.4
}
