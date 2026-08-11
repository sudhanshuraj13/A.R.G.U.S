import type { AutomationAction, AutomationIntent, TaskState } from "./automation"

export interface AIMessage {
  role: "system" | "user" | "assistant"
  content: string
}

export interface AIProvider {
  name: "openai" | "gemini" | "claude" | "groq" | "mock"
  complete(messages: AIMessage[]): Promise<string>
}

export interface IntentExtractor {
  extract(command: string): Promise<AutomationIntent>
}

export interface Planner {
  plan(state: TaskState): Promise<AutomationAction[]>
}
