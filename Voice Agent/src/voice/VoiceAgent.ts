export class VoiceAgent {
  cleanup(rawTranscript: string): string {
    return rawTranscript
      .trim()
      .replace(/\s+/g, " ")
      .replace(/\bplease\b/gi, "")
      .replace(/\bum+\b|\buh+\b|\blike\b/gi, "")
      .replace(/\s+/g, " ")
      .trim()
  }

  normalizeCommand(rawTranscript: string): string {
    const cleaned = this.cleanup(rawTranscript)
    if (!cleaned) {
      return cleaned
    }

    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
  }
}
