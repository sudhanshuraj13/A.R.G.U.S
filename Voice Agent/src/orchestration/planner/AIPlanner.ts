import type { AutomationAction, ActionKind, TaskState } from "~/types/automation"
import type { AIProvider, Planner } from "~/types/providers"
import { TinyFishClient, type TinyFishSearchResult } from "~/tinyfish/TinyFishClient"
import { createId } from "~/utils/id"
import { BasicPlanner } from "./BasicPlanner"

interface PlannedActionPayload {
  kind: ActionKind
  description: string
  target?: string
  value?: string
  url?: string
}

export class AIPlanner implements Planner {
  private readonly structuredPlanner = new BasicPlanner()

  constructor(
    private readonly ai: AIProvider,
    private readonly tinyfish: TinyFishClient
  ) {}

  async plan(state: TaskState): Promise<AutomationAction[]> {
    const structuredActions = await this.structuredPlanner.plan(state)
    if (structuredActions.length > 0) {
      return structuredActions
    }

    const context = await this.loadTinyFishContext(state.goal)
    const response = await this.ai.complete([
      {
        role: "system",
        content:
          "You are ARGUS, a browser automation planner. Return only JSON with an actions array. Each action must use kind navigate, new_tab, click, type, search, scroll, wait, summarize, or extract. Use new_tab when the user wants to open a new browser tab. Prefer direct URLs for website searches."
      },
      {
        role: "user",
        content: JSON.stringify({
          goal: state.goal,
          currentUrl: globalThis.location?.href,
          tinyfishSearchResults: context,
          schema: {
            actions: [
              {
                kind: "navigate",
                description: "Open or search a website",
                url: "https://example.com"
              }
            ]
          }
        })
      }
    ])

    const parsed = parsePlannerResponse(response)
    return parsed.map((action) => ({
      id: createId("action"),
      kind: action.kind,
      description: action.description,
      ...(action.target ? { target: action.target } : {}),
      ...(action.value ? { value: action.value } : {}),
      ...(action.url ? { url: action.url } : {})
    }))
  }

  private async loadTinyFishContext(goal: string): Promise<TinyFishSearchResult[]> {
    try {
      return (await this.tinyfish.search(goal)).slice(0, 5)
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : "TinyFish search failed.")
    }
  }
}

function parsePlannerResponse(response: string): PlannedActionPayload[] {
  const jsonText = response.match(/```json\s*([\s\S]*?)```/i)?.[1] ?? response.match(/\{[\s\S]*\}/)?.[0] ?? response
  const parsed = JSON.parse(jsonText) as { actions?: PlannedActionPayload[] }
  const actions = parsed.actions ?? []

  return actions.filter((action) => action.kind && action.description)
}
