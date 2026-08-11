import { useEffect, useMemo, useRef } from "react"
import { DomBrowserRuntime } from "~/automation/browser/DomRuntime"
import { ArgusController } from "~/orchestration/ArgusController"
import { ProviderSettingsStore } from "~/settings/ProviderSettings"
import { requireApiKeys } from "~/settings/requireApiKeys"
import { useArgusStore } from "~/state/argusStore"
import type { TaskState } from "~/types/automation"
import { VoiceInput } from "~/voice/speech/VoiceInput"
import { VoiceOutput } from "~/voice/speech/VoiceOutput"
import { WakeWordEngine } from "~/voice/wakeword/WakeWordEngine"
import { ApprovalModal } from "./approvals/ApprovalModal"
import { Notifications } from "./components/Notifications"

import { VoiceBubble } from "./voiceBubble/VoiceBubble"
import "./styles.css"

export function ArgusApp() {
  const store = useArgusStore()
  const runtime = useMemo(() => new DomBrowserRuntime(), [])
  const controller = useMemo(() => new ArgusController(() => runtime.getActivePage()), [runtime])
  const settingsStore = useMemo(() => new ProviderSettingsStore(), [])
  const voiceOutput = useMemo(() => new VoiceOutput(), [])
  const voiceInputRef = useRef<VoiceInput | null>(null)

  const submitCommand = async (command: string) => {
    try {
      const settings = await settingsStore.load()
      store.setSettings(settings)
      requireApiKeys(settings)
      runtime.setAgentQLApiKey(settings.agentqlApiKey)

      store.setStatus("planning")
      const task = await controller.prepareCommand(command, settings)
      store.setTask(task)
      const spokenReply = getSpokenReply(task)
      if (spokenReply) {
        voiceOutput.speak(spokenReply)
        store.notify({ type: "info", message: spokenReply })
      }
      store.notify({ type: task.status === "failed" ? "error" : "info", message: `Prepared ${task.pendingActions.length} action(s).` })

      if (task.pendingActions.length === 0) {
        return
      }

      const completedTask = await controller.executePreparedTask(task, {
        onTaskUpdate: store.setTask,
        onApprovalRequired: store.addApproval
      })
      store.setTask(completedTask)
      store.notify({ type: completedTask.status === "completed" ? "success" : "error", message: getTaskNotificationMessage(completedTask) })
    } catch (error) {
      store.notify({ type: "error", message: error instanceof Error ? error.message : "ARGUS could not prepare the command." })
    }
  }

  const toggleListening = () => {
    if (store.isListening) {
      voiceInputRef.current?.stop()
      voiceInputRef.current = null
      store.setListening(false)
      return
    }

    const input = new VoiceInput({
      onTranscript: (transcript, isFinal) => {
        if (!isFinal) return

        const command = transcript.trim()
        if (command) {
          const state = useArgusStore.getState()
          
          if (state.approvals.length > 0) {
            const activeApproval = state.approvals[0]
            const isApprove = /^(approve|okay|ok|proceed|yes|go ahead|do it|confirm|sure)$/i.test(command)
            const isReject = /^(reject|cancel|no|stop|abort|don't)$/i.test(command)

            if (isApprove) {
              state.resolveApproval(activeApproval.id)
              state.notify({ type: "success", message: "Action approved via voice." })
            } else if (isReject) {
              state.resolveApproval(activeApproval.id)
              state.setStatus("blocked")
              state.notify({ type: "warning", message: "Action rejected via voice." })
            } else {
              state.notify({ type: "warning", message: `Awaiting approval. Say "approve" or "reject".` })
            }
          } else {
            void submitCommand(command)
          }

          voiceInputRef.current?.stop()
          voiceInputRef.current = null
          store.setListening(false)
        }
      },
      onError: (message) => {
        store.notify({ type: "error", message })
        voiceInputRef.current = null
        store.setListening(false)
      },
      onEnd: () => {
        voiceInputRef.current = null
        store.setListening(false)
      }
    })

    voiceInputRef.current = input
    if (input.start()) {
      store.setListening(true)
    } else {
      voiceInputRef.current = null
    }
  }

  // Continuous Wake Word Listener
  useEffect(() => {
    if (!store.isWakeWordArmed || store.isListening) {
      return
    }

    const engine = new WakeWordEngine(
      (command) => {
        voiceOutput.speak("Yes?")
        if (command) {
          void submitCommand(command)
        } else {
          // They just said "hey argus", trigger active listening so they can speak the command
          toggleListening()
        }
      },
      (running) => {
        // We could update a small UI indicator here if needed
      },
      (message) => {
        store.notify({ type: "warning", message })
      }
    )

    engine.start()

    return () => {
      engine.stop()
    }
  }, [store.isWakeWordArmed, store.isListening])

  return (
    <>
      <VoiceBubble onToggleListening={toggleListening} />
      <ApprovalModal
        onApprove={(id) => {
          store.resolveApproval(id)
          store.notify({ type: "info", message: "Approval recorded." })
        }}
        onReject={(id) => {
          store.resolveApproval(id)
          store.setStatus("blocked")
          store.notify({ type: "warning", message: "Action rejected." })
        }}
      />
      <Notifications />
    </>
  )
}

function getTaskNotificationMessage(task: { status: string; logs: Array<{ message: string }> }): string {
  if (task.status === "failed") {
    return task.logs.at(-1)?.message ?? "Task failed."
  }

  const message = task.logs.at(-1)?.message ?? "Task completed."
  return message.length > 180 ? `${message.slice(0, 177)}...` : message
}

function getSpokenReply(task: Pick<TaskState, "intent" | "pendingActions">): string | undefined {
  const intent = task.intent
  if (!intent) return undefined

  if (intent.action === "play" && intent.website === "youtube" && intent.query) {
    const dynamicDesc = task.pendingActions?.[0]?.description
    return dynamicDesc ?? `Searching on YouTube for ${intent.query} and playing a video.`
  }

  if (intent.action === "search" && intent.website && intent.query) {
    return `Searching ${intent.website} for ${intent.query}.`
  }

  if (intent.action === "open" && intent.website) {
    return `Opening ${intent.website}.`
  }

  if (intent.action === "ask" && intent.query) {
    return `Let me search that for you.`
  }

  if (intent.action === "new_tab") {
    return `Opening a new tab.`
  }

  return undefined
}
