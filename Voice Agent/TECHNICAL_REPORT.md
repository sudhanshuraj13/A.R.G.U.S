# ARGUS Technical Report

## 1. What problem does the automation solve?
Navigating the web, filling out forms, and executing multi-step browsing tasks require significant manual interaction. ARGUS solves this by providing a voice-first, AI-powered browser automation assistant. It translates natural language commands into autonomous actions (e.g., clicking, typing, searching, navigating), making web browsing hands-free, highly accessible, and efficient while maintaining strict safety boundaries.

## 2. How does it work technically?
The extension operates through a pipeline of sequential steps:
1. **Voice Capture:** Uses the browser's Web Speech API with an optimized stability timer to rapidly capture commands without waiting for long silence gaps.
2. **Intent Extraction:** The raw text is passed to an Intent Extractor (`RuleBasedIntentExtractor`) to identify the core goal (e.g., search, open, click, ask).
3. **Planning & Orchestration:** A planner (powered by LangGraph and `AIPlanner` or `BasicPlanner`) converts the intent into an array of concrete `AutomationAction` objects (e.g., `navigate`, `type`, `click`).
4. **Safety & Permissions:** Before execution, a `RiskClassifier` and `PermissionSystem` evaluate each action. Safe actions proceed, while risky actions (e.g., "purchase", "delete") are paused for user approval or blocked entirely.
5. **Element Resolution:** To find elements on the page without relying on brittle CSS selectors, the `CascadingElementResolver` tries multiple strategies: Accessibility locators, Role/Text matching, and AgentQL AI-based resolution.
6. **Execution:** The `ExecutionEngine` runs the actions inside the `DomBrowserRuntime` (via content scripts injected into the active tab), while privileged actions like opening new tabs are routed through the Background Service Worker.
7. **State Management:** All task history, logs, approvals, and UI states are managed centrally using Zustand.

## 3. What tools/frameworks were used and how are they used?

### Extension & Frontend Frameworks
- **[Plasmo](https://docs.plasmo.com/) (React 18 + TypeScript):**
  - **What it is:** A modern browser extension framework that makes building extensions as easy as building Next.js web applications. It handles bundling, manifest generation, and hot-reloading.
  - **How we use it:** Used as the foundational build system for ARGUS. It bundles the React UI components, the background service worker (`background.ts`), and content scripts, ensuring they compile seamlessly to a Chrome Manifest V3 (MV3) extension.
- **Zustand:**
  - **What it is:** A small, fast, and scalable state-management solution for React.
  - **How we use it:** Powers `useArgusStore` (`src/state/argusStore.ts`) to manage global state across the side panel. It tracks the current automation task, execution logs, pending user approvals, and UI notifications without complex boilerplate.
- **Tailwind CSS & Framer Motion:**
  - **What they are:** Tailwind is a utility-first CSS framework for rapid UI styling. Framer Motion is a production-ready motion library for React.
  - **How we use them:** Tailwind is used to create the modern, glassmorphic UI of the extension's side panel. Framer Motion handles micro-animations, such as the pulsing voice capture bubble and sliding notifications, providing premium visual feedback.

### AI & Automation Libraries
- **LangGraph (`@langchain/langgraph`):**
  - **What it is:** A library for building stateful, multi-actor applications with LLMs, used to create cyclical graphs for agentic workflows.
  - **How we use it:** Powers the core decision loop (`ArgusGraph`). It orchestrates the flow from intent extraction to planning, executing, and validating browser actions, allowing the AI to evaluate outcomes and retry steps if they fail.
- **Playwright (Concepts & Abstractions):**
  - **What it is:** An industry-standard framework for Web Testing and Automation.
  - **How we use it:** Because Playwright's Node.js APIs cannot run inside a Chrome Extension sandbox, ARGUS adopts Playwright's *design patterns* (e.g., `LocatorLike`, `BrowserPage`). We built a custom `DomBrowserRuntime` that mimics Playwright's behavior using native DOM events (clicks, typing) injected via extension content scripts.
- **AgentQL (`agentql`):**
  - **What it is:** An AI-powered query language for the web that finds UI elements based on their semantic meaning rather than brittle CSS selectors (e.g., finding a "checkout button" even if the class names change).
  - **How we use it:** Acts as the heavy-lifter in our `CascadingElementResolver`. If standard DOM accessibility checks fail to find an element, ARGUS queries AgentQL to visually/semantically locate the target element on the current page.
- **TinyFish API:**
  - **What it is:** A suite of APIs designed for AI agents to search the web and extract clean markdown from web pages.
  - **How we use it:** Managed by the `TinyFishClient`. During the AI Planning phase (`AIPlanner`), ARGUS uses TinyFish to execute a web search based on the user's goal. It feeds the top 5 results (URLs, titles, snippets) directly into the LLM prompt. This grounds the AI in reality, allowing it to generate accurate navigation URLs instead of hallucinating them.

### How TinyFish and Playwright Work Together (The Automation Loop)
The smoothness of ARGUS comes from the separation of "world knowledge" and "physical execution":
1. **Planning with TinyFish:** When a user asks "Buy me a blue shirt on Amazon", the `AIPlanner` first asks TinyFish to search for this. TinyFish returns the exact URL for the search results page. The LLM uses this to output a JSON plan: `[{ kind: "navigate", url: "https://amazon.com/s?k=blue+shirt" }, { kind: "click", target: "first blue shirt" }]`.
2. **Execution with Playwright / AgentQL:** The `ExecutionEngine` receives the plan. It uses the custom Playwright `DomBrowserRuntime` to navigate the active tab to the TinyFish-provided URL. Once the page loads, ARGUS uses AgentQL to visually locate the "first blue shirt" and uses Playwright's synthetic DOM events to securely click it. 
*TinyFish provides the map; Playwright drives the car.*

### Core Browser APIs
- **Web Speech API:**
  - **What it is:** A native browser API built into Chrome for speech recognition (Speech-to-Text) and synthesis (Text-to-Speech).
  - **How we use it:** Captures the user's microphone input in `VoiceInput.ts` to transcribe spoken commands in real-time, driving the entire automation loop. Used in `VoiceOutput.ts` to provide audible status updates back to the user.
- **Chrome Side Panel API (`chrome.sidePanel`):**
  - **What it is:** A Chrome Manifest V3 API that allows extensions to display persistent UI anchored to the side of the browser window.
  - **How we use it:** Hosts the main ARGUS React application. This ensures the assistant's UI stays open and maintains context even when the user navigates across different tabs, opens new tabs, or redirects between websites.

## 4. What features are completed?
- **Fast Voice Input:** Optimized speech recognition that triggers instantly upon detecting a stable interim transcript.
- **Side Panel UI:** A persistent, glassmorphic UI that survives tab changes and handles user approvals and notifications.
- **Cascading Element Resolution:** Robust targeting of DOM elements using accessibility trees, text matching, and AgentQL fallbacks.
- **Safety System:** Automated risk classification that intercepts dangerous operations and prompts the user for manual approval via the UI.
- **DOM Automation:** Native browser automation for navigating, clicking, typing, scrolling, and waiting.
- **Provider Settings Integration:** Dynamic integration of external AI providers (OpenAI, Anthropic, etc.) and API keys.

## 5. What challenges were faced and solved?
- **Slow Voice Recognition:** The default Web Speech API `continuous=true` mode waited up to 5 seconds to finalize transcripts. *Solution:* Re-engineered `VoiceInput.ts` to use single-utterance mode with a custom 1.2s interim stability timer and a 3s silence timeout, resulting in 3x faster response times.
- **Extension Sandbox Limitations:** Running Playwright/AgentQL directly inside a Chrome Extension is restricted due to Node.js dependency requirements and cross-origin policies. *Solution:* Built a custom `DomBrowserRuntime` that leverages Chrome Content Scripts to execute standard DOM events, abstracting it behind a Playwright-like interface.
- **Unreliable Selectors:** Hardcoded CSS selectors break when websites update. *Solution:* Implemented a cascading resolver that prioritizes accessibility roles/text and falls back to semantic AI resolution (AgentQL/Vision).

## 6. What is the current status and limitations?
- **Status:** The MVP is fully functional. It captures voice input, displays a modern side-panel UI, extracts intents, plans actions, enforces safety, and executes commands on the DOM.
- **Limitations:** 
  - Voice recognition relies on the Web Speech API, which varies in quality depending on the browser (e.g., Chrome vs. Brave).
  - Heavy reliance on external API keys (AgentQL, TinyFish, LLMs) for advanced planning and resolution.
  - Complex multi-page workflows or heavy CAPTCHAs can disrupt the `DomBrowserRuntime`.

## 7. How can another developer run or extend it?
**To Run:**
1. Clone the repository and run `npm install`.
2. Run `npm run dev` to start the Plasmo development server.
3. Open Chrome and navigate to `chrome://extensions/`.
4. Enable "Developer mode" and click "Load unpacked". Select the `build/chrome-mv3-dev` directory.
5. Click the extension icon to open the ARGUS Side Panel.

**To Extend:**
- **Add New Intents:** Modify `src/orchestration/intent/RuleBasedIntentExtractor.ts` to recognize new command patterns.
- **Improve AI Planning:** Enhance `src/orchestration/planner/AIPlanner.ts` by integrating new LLM providers or complex prompt chains.
- **New Element Resolvers:** Add custom computer vision or DOM traversal strategies inside `src/automation/resolver/` and register them in the `CascadingElementResolver`.
- **Custom Actions:** Expand `ActionKind` in `types/automation.ts` and implement the execution logic inside `src/automation/browser/DomRuntime.ts`.
