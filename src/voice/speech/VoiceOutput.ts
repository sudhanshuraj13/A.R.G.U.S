export class VoiceOutput {
  private voicesLoaded = false

  constructor() {
    // The browser loads voices asynchronously. We need to trigger the load
    // early so they are ready when the user issues a command.
    if ("speechSynthesis" in window) {
      const loadVoices = () => {
        this.voicesLoaded = true
        window.speechSynthesis.removeEventListener("voiceschanged", loadVoices)
      }
      window.speechSynthesis.addEventListener("voiceschanged", loadVoices)
      // Trigger initial load
      window.speechSynthesis.getVoices()
    }
  }

  private getBestVoice(): SpeechSynthesisVoice | null {
    const voices = window.speechSynthesis.getVoices()
    if (voices.length === 0) return null

    // 1. Prefer high-quality cloud/Google voices (sounds very natural in Chrome)
    const googleVoice = voices.find((v) => v.name.includes("Google") && v.lang.startsWith("en"))
    if (googleVoice) return googleVoice

    // 2. Prefer Microsoft Natural or Apple Premium voices
    const premiumVoice = voices.find((v) => (v.name.includes("Natural") || v.name.includes("Premium")) && v.lang.startsWith("en"))
    if (premiumVoice) return premiumVoice

    // 3. Fallback to any English voice, or just the first available
    return voices.find((v) => v.lang.startsWith("en")) ?? voices[0]
  }

  speak(message: string): void {
    if (!message.trim() || !("speechSynthesis" in window)) {
      return
    }

    // Cancel any ongoing speech
    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(message)
    
    // Apply the best available voice
    const voice = this.getBestVoice()
    if (voice) {
      utterance.voice = voice
    }

    // Tweak rate and pitch for a slightly more natural cadence
    utterance.rate = 1.05
    utterance.pitch = 1.0

    window.speechSynthesis.speak(utterance)
  }
}
