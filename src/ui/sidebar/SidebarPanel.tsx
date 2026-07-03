import type { CSSProperties } from "react"
import { useArgusStore } from "~/state/argusStore"
import { SettingsPanel } from "~/ui/settings/SettingsPanel"

interface SidebarPanelProps {
  onSubmit(command: string): void
}

export function SidebarPanel({ onSubmit }: SidebarPanelProps) {
  const { currentTask, sidebarOpen, setSidebarOpen } = useArgusStore()

  if (!sidebarOpen) return null

  return (
    <aside style={panelStyle}>
      <header style={headerStyle}>
        <div>
          <h1 style={titleStyle}>ARGUS</h1>
          <p style={statusStyle}>{currentTask?.status ?? "idle"}</p>
        </div>
        <button style={closeBtnStyle} onClick={() => setSidebarOpen(false)} type="button">
          ✕
        </button>
      </header>

      <CommandBox onSubmit={onSubmit} />
      <SettingsPanel />

      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Current Task</h2>
        <p style={goalStyle}>{currentTask?.goal ?? "No task running."}</p>
      </section>

      <section style={sectionStyle}>
        <h2 style={sectionTitleStyle}>Execution Steps</h2>
        <div style={stepsListStyle}>
          {currentTask?.pendingActions.map((action) => (
            <div key={action.id} style={stepStyle}>
              {action.description}
            </div>
          ))}
          {currentTask?.completedSteps.map((action) => (
            <div key={action.id} style={completedStepStyle}>
              ✓ {action.description}
            </div>
          ))}
        </div>
      </section>

      <section style={logsAreaStyle}>
        <h2 style={sectionTitleStyle}>Logs</h2>
        <div style={stepsListStyle}>
          {(currentTask?.logs ?? []).map((log) => (
            <div key={log.id} style={logStyle}>
              <span style={logLevelStyle(log.level)}>{log.level}</span> {log.message}
            </div>
          ))}
        </div>
      </section>
    </aside>
  )
}

function CommandBox({ onSubmit }: SidebarPanelProps) {
  return (
    <form
      style={formStyle}
      onSubmit={(event) => {
        event.preventDefault()
        const form = event.currentTarget
        const input = new FormData(form).get("command")
        if (typeof input === "string" && input.trim()) {
          onSubmit(input)
          form.reset()
        }
      }}
    >
      <label style={labelStyle} htmlFor="argus-command">
        Command
      </label>
      <div style={inputRowStyle}>
        <input
          id="argus-command"
          name="command"
          style={inputStyle}
          placeholder="Search gaming headphones on Amazon"
        />
        <button style={runBtnStyle} type="submit">
          Run
        </button>
      </div>
    </form>
  )
}

// ─── Styles (translucent grey/black glass) ──────────────────────────────────
const panelStyle: CSSProperties = {
  position: "fixed",
  right: 16,
  top: 16,
  zIndex: 2147483646,
  display: "flex",
  flexDirection: "column",
  height: "calc(100vh - 2rem)",
  width: 380,
  maxWidth: "calc(100vw - 2rem)",
  borderRadius: 14,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  background: "rgba(22, 22, 26, 0.82)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  boxShadow: "0 24px 80px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.04)",
  color: "#E5E7EB",
  fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  overflow: "hidden"
}

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "14px 16px",
  borderBottom: "1px solid rgba(255, 255, 255, 0.06)"
}

const titleStyle: CSSProperties = {
  fontSize: 15,
  fontWeight: 700,
  color: "rgba(255, 255, 255, 0.9)",
  margin: 0
}

const statusStyle: CSSProperties = {
  fontSize: 11,
  color: "rgba(156, 163, 175, 0.7)",
  margin: 0
}

const closeBtnStyle: CSSProperties = {
  width: 28,
  height: 28,
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.06)",
  background: "rgba(255, 255, 255, 0.04)",
  color: "rgba(156, 163, 175, 0.7)",
  fontSize: 12,
  cursor: "pointer",
  fontFamily: "inherit"
}

const sectionStyle: CSSProperties = {
  padding: "12px 16px",
  borderBottom: "1px solid rgba(255, 255, 255, 0.05)"
}

const sectionTitleStyle: CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  color: "rgba(156, 163, 175, 0.7)",
  margin: 0,
  textTransform: "uppercase",
  letterSpacing: 0.5
}

const goalStyle: CSSProperties = {
  marginTop: 6,
  fontSize: 13,
  color: "rgba(229, 231, 235, 0.85)",
  lineHeight: 1.45
}

const stepsListStyle: CSSProperties = {
  marginTop: 8,
  display: "flex",
  flexDirection: "column",
  gap: 4
}

const stepStyle: CSSProperties = {
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.05)",
  background: "rgba(255, 255, 255, 0.02)",
  fontSize: 12,
  color: "rgba(209, 213, 219, 0.85)"
}

const completedStepStyle: CSSProperties = {
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid rgba(156, 163, 175, 0.15)",
  background: "rgba(156, 163, 175, 0.06)",
  fontSize: 12,
  color: "rgba(156, 163, 175, 0.8)"
}

const logsAreaStyle: CSSProperties = {
  flex: 1,
  minHeight: 0,
  overflow: "auto",
  padding: "12px 16px"
}

const logStyle: CSSProperties = {
  fontSize: 11,
  color: "rgba(156, 163, 175, 0.6)",
  marginBottom: 4
}

function logLevelStyle(level: string): CSSProperties {
  const colors: Record<string, string> = {
    info: "rgba(148, 163, 184, 0.8)",
    warn: "rgba(250, 204, 21, 0.7)",
    error: "rgba(248, 113, 113, 0.8)"
  }
  return {
    fontWeight: 700,
    textTransform: "uppercase",
    color: colors[level] ?? "rgba(156, 163, 175, 0.6)"
  }
}

const formStyle: CSSProperties = {
  padding: "12px 16px",
  borderBottom: "1px solid rgba(255, 255, 255, 0.05)"
}

const labelStyle: CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: "rgba(156, 163, 175, 0.7)"
}

const inputRowStyle: CSSProperties = {
  display: "flex",
  gap: 8,
  marginTop: 8
}

const inputStyle: CSSProperties = {
  flex: 1,
  minWidth: 0,
  padding: "9px 12px",
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  background: "rgba(255, 255, 255, 0.04)",
  color: "#E5E7EB",
  fontSize: 13,
  outline: "none",
  fontFamily: "inherit"
}

const runBtnStyle: CSSProperties = {
  padding: "9px 14px",
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  background: "rgba(255, 255, 255, 0.06)",
  color: "rgba(229, 231, 235, 0.85)",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
  fontFamily: "inherit"
}
