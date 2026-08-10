import type { AIMessage, AIProvider } from "~/types/providers"

export class MockProvider implements AIProvider {
  readonly name = "mock" as const

  async complete(messages: AIMessage[]): Promise<string> {
    return messages.at(-1)?.content ?? ""
  }
}
