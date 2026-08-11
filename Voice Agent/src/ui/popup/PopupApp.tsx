import { useMemo } from "react"
import { ArgusController } from "~/orchestration/ArgusController"
import { ProviderSettingsStore } from "~/settings/ProviderSettings"
import { requireApiKeys } from "~/settings/requireApiKeys"
import { useArgusStore } from "~/state/argusStore"
import { SettingsPanel } from "~/ui/settings/SettingsPanel"
import { Notifications } from "../components/Notifications"
import "../styles.css"

export function PopupApp() {
  const store = useArgusStore()
  const controller = useMemo(() => new ArgusController(), [])
  const settingsStore = useMemo(() => new ProviderSettingsStore(), [])

  const submitCommand = async (command: string) => {
    try {
      const settings = await settingsStore.load()
      store.setSettings(settings)
      requireApiKeys(settings)

      const task = await controller.prepareCommand(command, settings)
      store.setTask(task)
      store.notify({ type: task.status === "failed" ? "error" : "info", message: `Prepared ${task.pendingActions.length} action(s). Open the page bubble to execute in the active tab.` })
    } catch (error) {
      store.notify({ type: "error", message: error instanceof Error ? error.message : "ARGUS could not prepare the command." })
    }
  }

  const openSidePanel = () => {
    chrome.runtime.sendMessage({ type: "ARGUS_OPEN_SIDE_PANEL" }).catch(() => {
      // Side panel may already be open or not available
    })
    window.close()
  }

  return (
    <main style={rootStyle}>
      <header style={headerStyle}>
        <div style={logoRowStyle}>
          <div style={logoStyle}>
            <span style={logoLetterStyle}>A</span>
          </div>
          <div>
            <h1 style={titleStyle}>ARGUS</h1>
            <p style={subtitleStyle}>Voice-first browser automation</p>
          </div>
        </div>
      </header>

      <div style={contentStyle}>
        <button type="button" style={primaryBtnStyle} onClick={openSidePanel}>
          Open ARGUS Side Panel
        </button>
        <p style={hintStyle}>
          💡 Tip: Click the ARGUS toolbar icon to open the side panel directly — it works on every tab including new tabs.
        </p>
      </div>

      <form
        style={formStyle}
        onSubmit={(event) => {
          event.preventDefault()
          const form = event.currentTarget
          const command = new FormData(form).get("command")
          if (typeof command === "string" && command.trim()) {
            void submitCommand(command)
            form.reset()
          }
        }}
      >
        <label style={labelStyle} htmlFor="argus-popup-command">
          Quick Command
        </label>
        <div style={inputRowStyle}>
          <input
            id="argus-popup-command"
            name="command"
            style={inputStyle}
            placeholder="Search headphones on Amazon"
          />
          <button style={runBtnStyle} type="submit">
            Run
          </button>
        </div>
      </form>

      <SettingsPanel />
      <TaskPreview />
      <Notifications />
    </main>
  )
}

function TaskPreview() {
  const currentTask = useArgusStore((state) => state.currentTask)

  return (
    <section style={previewStyle}>
      <h2 style={previewTitleStyle}>Current Task</h2>
      <p style={previewGoalStyle}>{currentTask?.goal ?? "No task prepared yet."}</p>
      <div style={stepsStyle}>
        {(currentTask?.pendingActions ?? []).map((action) => (
          <div key={action.id} style={stepStyle}>
            {action.description}
          </div>
        ))}
      </div>
    </section>
  )
}

// ─── Inline styles (dark theme matching side panel) ─────────────────────────
import type { CSSProperties } from "react"

const rootStyle: CSSProperties = {
  width: 390,
  background: "linear-gradient(180deg, #0F172A, #111827)",
  color: "#F3F4F6",
  fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
}

const headerStyle: CSSProperties = {
  padding: "14px 16px",
  borderBottom: "1px solid rgba(255, 255, 255, 0.06)"
}

const logoRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10
}

const logoStyle: CSSProperties = {
  display: "grid",
  placeItems: "center",
  width: 34,
  height: 34,
  borderRadius: 8,
  background: "linear-gradient(135deg, #0F766E, #14B8A6)"
}

const logoLetterStyle: CSSProperties = {
  fontSize: 16,
  fontWeight: 800,
  color: "#FFFFFF"
}

const titleStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 700,
  color: "#F9FAFB",
  margin: 0
}

const subtitleStyle: CSSProperties = {
  fontSize: 11,
  color: "#6B7280",
  margin: 0
}

const contentStyle: CSSProperties = {
  padding: "14px 16px",
  borderBottom: "1px solid rgba(255, 255, 255, 0.06)"
}

const primaryBtnStyle: CSSProperties = {
  width: "100%",
  padding: "10px 16px",
  borderRadius: 10,
  border: "none",
  background: "linear-gradient(135deg, #0F766E, #14B8A6)",
  color: "#FFFFFF",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
  fontFamily: "inherit"
}

const hintStyle: CSSProperties = {
  marginTop: 10,
  fontSize: 11,
  color: "#6B7280",
  lineHeight: 1.5
}

const formStyle: CSSProperties = {
  padding: "14px 16px",
  borderBottom: "1px solid rgba(255, 255, 255, 0.06)"
}

const labelStyle: CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: "#9CA3AF"
}

const inputRowStyle: CSSProperties = {
  display: "flex",
  gap: 8,
  marginTop: 8
}

const inputStyle: CSSProperties = {
  flex: 1,
  minWidth: 0,
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  background: "rgba(255, 255, 255, 0.04)",
  color: "#F3F4F6",
  fontSize: 12,
  outline: "none",
  fontFamily: "inherit"
}

const runBtnStyle: CSSProperties = {
  padding: "8px 14px",
  borderRadius: 8,
  border: "none",
  background: "#1F2937",
  color: "#D1D5DB",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
  fontFamily: "inherit"
}

const previewStyle: CSSProperties = {
  padding: "14px 16px",
  maxHeight: 200,
  overflowY: "auto"
}

const previewTitleStyle: CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: "#9CA3AF",
  margin: 0
}

const previewGoalStyle: CSSProperties = {
  marginTop: 6,
  fontSize: 12,
  color: "#D1D5DB"
}

const stepsStyle: CSSProperties = {
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
  color: "#D1D5DB"
}
