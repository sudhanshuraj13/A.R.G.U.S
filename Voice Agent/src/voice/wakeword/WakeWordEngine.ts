import { WakeWordListener } from "./WakeWordListener"

export class WakeWordEngine {
  private recognition: SpeechRecognition | undefined
  private isRunning = false
  private readonly listener = new WakeWordListener()

  constructor(
    private readonly onWakeWordDetected: (command: string) => void,
    private readonly onStateChange: (running: boolean) => void,
    private readonly onError: (message: string) => void
  ) {}

  start(): void {
    if (this.isRunning) return
    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition
    if (!Recognition) return

    this.recognition = new Recognition()
    this.recognition.continuous = true // Keep listening continuously
    this.recognition.interimResults = true // We want to catch the wake word ASAP
    this.recognition.lang = "en-US"

    this.recognition.onresult = (event) => {
      // Get the latest interim or final result
      const latest = event.results.item(event.results.length - 1)
      const transcript = latest[0].transcript.toLowerCase()

      const match = this.listener.detect(transcript)
      if (match) {
        // We heard the wake word!
        this.stop() // Pause the continuous listener
        
        // If there's a command attached (e.g. "hey argus open youtube")
        const command = match.command.trim()
        if (command) {
          this.onWakeWordDetected(command)
        } else {
          // They just said "hey argus", we should probably trigger the active listener
          this.onWakeWordDetected("")
        }
      }
    }

    this.recognition.onerror = (event) => {
      if (event.error === "no-speech") return // Ignore silence errors
      if (event.error === "not-allowed") {
        this.stop()
        this.onError("Microphone access denied for background listening. Click the bubble to grant permission.")
        return
      }
      // For other errors (like network), restart after a short delay
      this.restartLater()
    }

    this.recognition.onend = () => {
      if (this.isRunning) {
        // It stopped on its own (Chrome sometimes kills it), restart it
        this.recognition?.start()
      }
    }

    try {
      this.isRunning = true
      this.recognition.start()
      this.onStateChange(true)
    } catch {
      this.isRunning = false
      this.onStateChange(false)
    }
  }

  stop(): void {
    this.isRunning = false
    this.recognition?.stop()
    this.recognition = undefined
    this.onStateChange(false)
  }

  private restartLater(): void {
    if (!this.isRunning) return
    this.recognition?.stop()
    setTimeout(() => {
      if (this.isRunning) {
        try { this.recognition?.start() } catch {}
      }
    }, 1000)
  }
}
