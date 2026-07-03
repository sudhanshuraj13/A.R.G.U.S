type SpeechRecognitionCtor = new () => SpeechRecognition

interface SpeechRecognitionEventResult {
  readonly transcript: string
  readonly confidence: number
}

interface SpeechRecognitionResultListLike {
  readonly length: number
  item(index: number): { readonly 0: SpeechRecognitionEventResult; readonly isFinal: boolean }
}

interface SpeechRecognitionEventLike extends Event {
  readonly results: SpeechRecognitionResultListLike
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}

interface SpeechRecognitionErrorEventLike extends Event {
  readonly error?: string
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionCtor
    webkitSpeechRecognition?: SpeechRecognitionCtor
  }
}

export interface VoiceInputEvents {
  onTranscript(transcript: string, isFinal: boolean): void
  onError(error: string): void
  onEnd(): void
}

export class VoiceInput {
  private recognition: SpeechRecognition | undefined

  /** Timer that fires when the interim transcript has been stable long enough */
  private stabilityTimer: ReturnType<typeof setTimeout> | undefined

  /** Timer that fires when no speech is detected at all */
  private silenceTimer: ReturnType<typeof setTimeout> | undefined

  /** Last interim transcript received — used to detect stabilization */
  private lastInterim = ""

  /** Whether we already forwarded a final transcript for this session */
  private delivered = false

  /**
   * @param events       Callbacks for transcript / error / end
   * @param language     BCP-47 language tag (default "en-US")
   * @param silenceMs    Auto-stop if no speech detected within this period (ms)
   * @param stabilityMs  Treat an interim result as final when it hasn't changed for this long (ms)
   */
  constructor(
    private readonly events: VoiceInputEvents,
    private readonly language = "en-US",
    private readonly silenceMs = 3_000,
    private readonly stabilityMs = 1_200
  ) {}

  isSupported(): boolean {
    return Boolean(window.SpeechRecognition ?? window.webkitSpeechRecognition)
  }

  start(): boolean {
    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition
    if (!Recognition) {
      this.events.onError("Web Speech API is not available in this browser.")
      return false
    }

    this.delivered = false
    this.lastInterim = ""
    this.recognition = new Recognition()

    // Non-continuous: the engine will stop after one utterance,
    // producing a final result much faster than continuous mode.
    this.recognition.continuous = false
    this.recognition.interimResults = true
    this.recognition.lang = this.language

    this.recognition.onresult = (event) => {
      this.clearSilenceTimer()                               // user is speaking

      const latest = event.results.item(event.results.length - 1)
      const transcript = latest[0].transcript.trim()

      if (latest.isFinal) {
        this.deliver(transcript)
        return
      }

      // Forward interim transcript for live display
      this.events.onTranscript(transcript, false)

      // --- Stability-based early finalization ---
      // If the interim text hasn't changed for `stabilityMs`, treat it as final
      // so the user doesn't have to wait for the long browser silence gap.
      if (transcript && transcript === this.lastInterim) {
        // Same text — the timer is already running, let it fire
        return
      }
      this.lastInterim = transcript
      this.clearStabilityTimer()
      if (transcript) {
        this.stabilityTimer = setTimeout(() => {
          this.deliver(transcript)
        }, this.stabilityMs)
      }
    }

    this.recognition.onerror = (event) => {
      this.clearAllTimers()
      // "no-speech" is not really an error — just means the user didn't say anything
      if (event.error === "no-speech") {
        this.events.onEnd()
        return
      }
      const reason = event.error ? `Speech recognition failed: ${event.error}.` : "Speech recognition failed."
      this.events.onError(reason)
    }

    this.recognition.onend = () => {
      this.clearAllTimers()
      // If we received interim text but the engine stopped before marking it
      // final (e.g. very short utterance), deliver what we have.
      if (!this.delivered && this.lastInterim) {
        this.deliver(this.lastInterim)
        return                                               // deliver() calls onEnd
      }
      this.events.onEnd()
    }

    try {
      this.recognition.start()
      // Start silence timer — auto-stop if user never speaks
      this.silenceTimer = setTimeout(() => this.stop(), this.silenceMs)
      return true
    } catch (error) {
      this.recognition = undefined
      this.events.onError(error instanceof Error ? error.message : "Speech recognition could not start.")
      return false
    }
  }

  stop(): void {
    this.clearAllTimers()
    this.recognition?.stop()
    this.recognition = undefined
  }

  // ── private helpers ──────────────────────────────────────

  private deliver(transcript: string): void {
    if (this.delivered) return
    this.delivered = true
    this.clearAllTimers()
    this.recognition?.stop()
    this.recognition = undefined
    this.events.onTranscript(transcript, true)
    this.events.onEnd()
  }

  private clearStabilityTimer(): void {
    if (this.stabilityTimer !== undefined) {
      clearTimeout(this.stabilityTimer)
      this.stabilityTimer = undefined
    }
  }

  private clearSilenceTimer(): void {
    if (this.silenceTimer !== undefined) {
      clearTimeout(this.silenceTimer)
      this.silenceTimer = undefined
    }
  }

  private clearAllTimers(): void {
    this.clearStabilityTimer()
    this.clearSilenceTimer()
  }
}
