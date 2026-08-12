/**
 * BackendBridge.ts
 *
 * Polling bridge connecting the Chrome Extension with the RaspberryPiBackend.
 * Fetches pending voice commands sent from hardware (ESP32) or Postman and passes
 * them to ARGUS automation for execution.
 */

export interface PendingTask {
  task_id: string
  command: string
  status: string
}

export interface PendingTaskResponse {
  ok: boolean
  task: PendingTask | null
}

export class BackendBridge {
  private isPolling = false
  private timerId: any = null

  constructor(
    private readonly backendUrl: string = "http://127.0.0.1:8000",
    private readonly pollIntervalMs: number = 3000
  ) {}

  startPolling(onCommandReceived: (task: PendingTask) => Promise<string>): void {
    if (this.isPolling) return
    this.isPolling = true

    const poll = async () => {
      if (!this.isPolling) return

      try {
        const response = await fetch(`${this.backendUrl}/voice/pending`)
        if (response.ok) {
          const data: PendingTaskResponse = await response.json()
          if (data.ok && data.task) {
            console.log("[BackendBridge] Received task from RaspberryPiBackend:", data.task)
            await this.handleTask(data.task, onCommandReceived)
          }
        }
      } catch (err) {
        // Backend might be offline or restarting — silently swallow fetch errors
      }

      if (this.isPolling) {
        this.timerId = setTimeout(poll, this.pollIntervalMs)
      }
    }

    poll()
  }

  stopPolling(): void {
    this.isPolling = false
    if (this.timerId) {
      clearTimeout(this.timerId)
      this.timerId = null
    }
  }

  private async handleTask(
    task: PendingTask,
    executor: (task: PendingTask) => Promise<string>
  ): Promise<void> {
    try {
      const resultText = await executor(task)
      await this.sendResult(task.task_id, true, resultText, null)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      await this.sendResult(task.task_id, false, null, errorMessage)
    }
  }

  private async sendResult(
    taskId: string,
    ok: boolean,
    result: string | null,
    error: string | null
  ): Promise<void> {
    try {
      await fetch(`${this.backendUrl}/voice/result`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_id: taskId,
          ok,
          result,
          error,
        }),
      })
    } catch (err) {
      console.error("[BackendBridge] Failed to post result back to RaspberryPiBackend:", err)
    }
  }
}
