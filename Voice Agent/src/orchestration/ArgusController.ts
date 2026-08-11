import { ExecutionEngine, type ExecutionEvents } from "~/automation/execution/ExecutionEngine"
import { CascadingElementResolver } from "~/automation/resolver/CascadingElementResolver"
import { BasicActionValidator } from "~/automation/validation/ActionValidator"
import { PlaywrightRuntime } from "~/automation/playwright/PlaywrightRuntime"
import { HttpAIProvider } from "~/ai/providers/HttpAIProvider"
import type { ArgusProviderSettings } from "~/settings/ProviderSettings"
import { TinyFishClient } from "~/tinyfish/TinyFishClient"
import { TaskMemory } from "~/memory/TaskMemory"
import type { BrowserPage } from "~/types/runtime"
import type { TaskState } from "~/types/automation"
import { VoiceAgent } from "~/voice/VoiceAgent"
import { BasicPlanner } from "./planner/BasicPlanner"
import { AIPlanner } from "./planner/AIPlanner"
import { RuleBasedIntentExtractor } from "./intent/RuleBasedIntentExtractor"
import { ArgusGraph } from "./graph/ArgusGraph"
import { createTaskState } from "./createTaskState"

export class ArgusController {
  private readonly voiceAgent = new VoiceAgent()
  private readonly memory = new TaskMemory()

  constructor(private readonly pageProvider?: () => Promise<BrowserPage>) {}

  async prepareCommand(rawCommand: string, settings?: ArgusProviderSettings): Promise<TaskState> {
    const goal = this.voiceAgent.normalizeCommand(rawCommand)
    const graph = settings ? this.createApiBackedGraph(settings) : new ArgusGraph(new RuleBasedIntentExtractor(), new BasicPlanner())
    const task = await graph.prepare(createTaskState(goal))
    this.memory.rememberTask(task)
    return task
  }

  async executePreparedTask(state: TaskState, events: ExecutionEvents): Promise<TaskState> {
    if (!this.pageProvider) {
      throw new Error("No browser page provider is configured for execution.")
    }

    const engine = new ExecutionEngine(
      new PlaywrightRuntime(this.pageProvider),
      new CascadingElementResolver(),
      new BasicActionValidator()
    )

    const completedTask = await engine.run(state, events)
    this.memory.rememberTask(completedTask)
    return completedTask
  }

  private createApiBackedGraph(settings: ArgusProviderSettings): ArgusGraph {
    return new ArgusGraph(
      new RuleBasedIntentExtractor(),
      new AIPlanner(new HttpAIProvider(settings), new TinyFishClient(settings.tinyfishApiKey))
    )
  }
}
