import { motion, type MotionStyle, useDragControls } from "framer-motion"
import { type CSSProperties, useMemo } from "react"
import { useArgusStore } from "~/state/argusStore"

interface VoiceBubbleProps {
  onToggleListening(): void
}

export function VoiceBubble({ onToggleListening }: VoiceBubbleProps) {
  const controls = useDragControls()
  const { currentTask, isListening } = useArgusStore()
  const state = useMemo(() => {
    if (isListening) return "Listening"
    if (currentTask?.status === "executing") return "Thinking"
    if (currentTask?.status === "waiting_approval") return "Approval"
    if (currentTask?.status === "completed") return "Done"
    if (currentTask?.status === "failed") return "Failed"
    return "Ready"
  }, [currentTask?.status, isListening])

  return (
    <motion.div
      aria-label={`ARGUS assistant ${state}`}
      style={containerStyle}
      drag
      dragControls={controls}
      dragMomentum={false}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      <button
        type="button"
        aria-label="Toggle voice input"
        onClick={onToggleListening}
        style={bubbleStyle(isListening, currentTask?.status)}
      >
        {/* Glass highlight */}
        <span style={glassHighlightStyle} />

        {/* Listening pulse ring */}
        {isListening ? (
          <motion.span
            style={pulseRingStyle}
            animate={{ scale: [1, 1.4, 1], opacity: [0.6, 0, 0.6] }}
            transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
          />
        ) : null}

        {/* Executing orbit spinner */}
        {currentTask?.status === "executing" ? (
          <motion.span
            style={orbitStyle}
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
          />
        ) : null}

        {/* Letter */}
        <span style={letterStyle}>A</span>

        {/* Status dot */}
        <span style={dotStyle(isListening, currentTask?.status)} />
      </button>
    </motion.div>
  )
}

// ─── Container ──────────────────────────────────────────────────────────────
const containerStyle: MotionStyle = {
  position: "fixed",
  right: 20,
  bottom: 20,
  zIndex: 2147483647,
  display: "flex",
  alignItems: "center",
  gap: 8,
  pointerEvents: "auto",
  fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
}

// ─── Bubble ─────────────────────────────────────────────────────────────────
function bubbleStyle(isListening: boolean, status?: string): CSSProperties {
  const active = isListening || status === "executing"

  return {
    position: "relative",
    display: "grid",
    placeItems: "center",
    width: 56,
    height: 56,
    border: active
      ? "1px solid rgba(255, 255, 255, 0.18)"
      : "1px solid rgba(255, 255, 255, 0.08)",
    borderRadius: 999,
    background: active
      ? "linear-gradient(145deg, rgba(55, 55, 60, 0.85), rgba(30, 30, 35, 0.9))"
      : "linear-gradient(145deg, rgba(40, 40, 45, 0.72), rgba(20, 20, 24, 0.78))",
    color: "#FFFFFF",
    boxShadow: active
      ? "0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.1)"
      : "0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.06)",
    cursor: "pointer",
    overflow: "visible",
    backdropFilter: "blur(24px)",
    WebkitBackdropFilter: "blur(24px)",
    transition: "background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease"
  }
}

// ─── Glass highlight (top-left crescent) ────────────────────────────────────
const glassHighlightStyle: CSSProperties = {
  position: "absolute",
  top: 6,
  left: 10,
  width: 24,
  height: 10,
  borderRadius: 999,
  background: "linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.04))",
  pointerEvents: "none"
}

// ─── Listening pulse ────────────────────────────────────────────────────────
const pulseRingStyle: MotionStyle = {
  position: "absolute",
  width: 56,
  height: 56,
  borderRadius: 999,
  border: "2px solid rgba(200, 200, 210, 0.6)",
  pointerEvents: "none"
}

// ─── Thinking orbit ─────────────────────────────────────────────────────────
const orbitStyle: MotionStyle = {
  position: "absolute",
  width: 68,
  height: 68,
  borderRadius: 999,
  borderTop: "2px solid rgba(255, 255, 255, 0.7)",
  borderRight: "2px solid transparent",
  borderBottom: "2px solid rgba(255, 255, 255, 0.12)",
  borderLeft: "2px solid transparent",
  pointerEvents: "none"
}

// ─── Letter ─────────────────────────────────────────────────────────────────
const letterStyle: CSSProperties = {
  position: "relative",
  fontSize: 22,
  fontWeight: 800,
  lineHeight: 1,
  color: "rgba(255, 255, 255, 0.92)",
  textShadow: "0 1px 8px rgba(0, 0, 0, 0.4)"
}

// ─── Status dot ─────────────────────────────────────────────────────────────
function dotStyle(isListening: boolean, status?: string): CSSProperties {
  const color = isListening
    ? "#A0AEC0"           // cool grey when listening
    : status === "executing"
      ? "#D4D4D8"         // light zinc when thinking
      : status === "waiting_approval"
        ? "#F87171"       // soft red for approval
        : status === "failed"
          ? "#EF4444"     // red for failed
          : "#9CA3AF"     // neutral grey default

  return {
    position: "absolute",
    right: 4,
    bottom: 4,
    width: 11,
    height: 11,
    borderRadius: 999,
    background: color,
    border: "2px solid rgba(30, 30, 35, 0.9)",
    boxShadow: `0 0 10px ${color}55`
  }
}
