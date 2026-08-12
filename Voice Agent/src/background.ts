/**
 * ARGUS background service worker.
 *
 * Handles privileged Chrome API calls (e.g. tab creation) that cannot run
 * inside content scripts or the side-panel context.
 * Also opens the ARGUS side panel on extension icon click so that
 * ARGUS is accessible on every tab — including chrome://newtab.
 */

export interface ArgusBackgroundMessage {
  type: "ARGUS_NEW_TAB" | "ARGUS_EXECUTE_ON_TAB"
  url?: string
  command?: string
}

export interface ArgusBackgroundResponse {
  ok: boolean
  tabId?: number
  error?: string
}

// ─── Open side panel when the toolbar icon is clicked ────────────────────────
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {
  // Fallback: if setPanelBehavior is not supported, use action click listener
})

// ─── Message router ─────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener(
  (
    message: ArgusBackgroundMessage,
    _sender: chrome.runtime.MessageSender,
    sendResponse: (response: ArgusBackgroundResponse) => void
  ) => {
    if (message.type === "ARGUS_NEW_TAB") {
      chrome.tabs
        .create({ url: message.url ?? "chrome://newtab", active: true })
        .then((tab) => sendResponse({ ok: true, tabId: tab.id }))
        .catch((error) =>
          sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) })
        )
      return true
    }

    if (message.type === "ARGUS_EXECUTE_ON_TAB") {
      // Forward the command to the content script in the active tab
      chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
        if (!tab?.id) {
          sendResponse({ ok: false, error: "No active tab found." })
          return
        }
        chrome.tabs
          .sendMessage(tab.id, { type: "ARGUS_RUN_COMMAND", command: message.command })
          .then(() => sendResponse({ ok: true, tabId: tab.id }))
          .catch((error) =>
            sendResponse({ ok: false, error: error instanceof Error ? error.message : String(error) })
          )
      })
      return true
    }
  }
)

// ─── Hardware / RaspberryPiBackend Polling Bridge ────────────────────────────
import { BackendBridge } from "~/services/BackendBridge"

const bridge = new BackendBridge("http://127.0.0.1:8000", 3000)

bridge.startPolling(async (task) => {
  console.log(`[ARGUS Background] Executing command from hardware/Postman: "${task.command}"`)
  
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  if (!tab?.id) {
    throw new Error("No active browser tab found to run voice automation command.")
  }

  const response = await chrome.tabs.sendMessage(tab.id, {
    type: "ARGUS_RUN_COMMAND",
    command: task.command,
  })

  if (!response || !response.ok) {
    throw new Error(response?.error || "Failed to execute command in active browser tab.")
  }

  return response.result || `Command "${task.command}" dispatched to browser tab.`
})

