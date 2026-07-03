export interface WakeWordMatch {
  command: string
  wakeWord: string
}

export class WakeWordListener {
  constructor(
    private readonly wakeWords = [
      "hey argus",
      "argus",
      "hey august",
      "august",
      "hey argos",
      "argos",
      "hey arcus",
      "arcus",
      "hey guest",
      "a guest"
    ]
  ) {}

  detect(transcript: string): WakeWordMatch | null {
    const normalized = transcript.toLowerCase().replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim()
    const wakeWord = this.wakeWords.find((word) => normalized.startsWith(word))
    if (!wakeWord) {
      return null
    }

    return {
      wakeWord,
      command: normalized.slice(wakeWord.length).trim()
    }
  }
}
