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

- **RaspberryPiBackend & ESP32 Hardware Integration:**
  - **What it is:** A FastAPI Python backend running on Raspberry Pi paired with ESP32-CAM Smart Glasses hardware.
  - **How we use it:** `RaspberryPiBackend` exposes a `/voice/command` router (`app/routers/voice.py`) and a `BackendBridge` in the Chrome Extension. Hardware (ESP32) or Postman sends HTTP commands to the backend, which are fetched by the Chrome Extension background worker, executed natively on Chrome DOM using TinyFish/AgentQL, and reported back to `RaspberryPiBackend` to speak out results via `pyttsx3` Text-to-Speech audio.

### How TinyFish, Custom DOM, and RaspberryPiBackend Work Together (The Automation Loop)
The smoothness of ARGUS comes from the separation of "world knowledge", "physical execution", and "hardware integration":
1. **Hardware / Postman Command Ingestion:** The ESP32 Smart Glasses hardware or Postman collection posts a command (e.g. "Find me a blue T-shirt on Amazon") to `RaspberryPiBackend` (`POST /voice/command`).
2. **Bridge Relay:** The `BackendBridge` running in the `Voice Agent` Chrome Extension polls `http://localhost:8000/voice/pending`, picks up the command, and forwards it to the active browser tab.
3. **Planning with TinyFish:** The `AIPlanner` uses TinyFish search adapters to find the exact URL for the search results page. The LLM outputs structured browser action steps.
4. **Execution with Custom DOM Runtime:** The `ExecutionEngine` receives the plan and executes actions natively inside active Chrome tabs using custom DOM event injection, bypassing standard CDP/Playwright anti-bot restrictions.
5. **TTS Audio Output:** Upon task completion, the extension sends execution results (`POST /voice/result`) back to `RaspberryPiBackend`, which speaks the response out loud using `pyttsx3`.

## 4. What features are completed?
- **Fast Voice Input:** Optimized speech recognition that triggers instantly upon detecting a stable interim transcript.
- **Hardware & Backend Bridge:** Complete FastAPI integration (`/voice/command`, `/voice/pending`, `/voice/result`) allowing ESP32 smart glasses and Postman collections to drive browser automation.
- **Audible TTS Feedback:** Real-time spoken notifications via `pyttsx3` text-to-speech upon task completion.
- **Side Panel UI:** A persistent, glassmorphic UI that survives tab changes and handles user approvals and notifications.
- **Cascading Element Resolution:** Robust targeting of DOM elements using accessibility trees, text matching, and AgentQL fallbacks.
- **Safety System:** Automated risk classification that intercepts dangerous operations and prompts the user for manual approval via the UI.
- **DOM Automation:** Native browser automation for navigating, clicking, typing, scrolling, and waiting.
- **Provider Settings Integration:** Dynamic integration of external AI providers (OpenAI, Anthropic, etc.) and API keys.

## 5. What challenges were faced and solved?
- **CDP & Playwright Headless Limitations:** Standard Playwright over Chrome Developer Protocol (CDP) suffers from anti-bot blocking and lacks access to existing user browser sessions. *Solution:* Built a custom `DomBrowserRuntime` injected via Chrome Content Scripts combined with a `BackendBridge` that connects FastAPI backend commands directly to native Chrome tabs.
- **Slow Voice Recognition:** The default Web Speech API `continuous=true` mode waited up to 5 seconds to finalize transcripts. *Solution:* Re-engineered `VoiceInput.ts` to use single-utterance mode with a custom 1.2s interim stability timer and a 3s silence timeout, resulting in 3x faster response times.
- **Unreliable Selectors:** Hardcoded CSS selectors break when websites update. *Solution:* Implemented a cascading resolver that prioritizes accessibility roles/text and falls back to semantic AI resolution (AgentQL/Vision).

## 6. What is the current status and limitations?
- **Status:** The MVP is fully functional across hardware, backend, and extension layers. ESP32 smart glasses and Postman collections can trigger complex browser automation tasks, which are executed natively and announced via voice TTS.
- **Limitations:** 
  - Voice recognition relies on the Web Speech API or backend STT, which varies depending on environmental noise.
  - Heavy reliance on external API keys (AgentQL, TinyFish, LLMs) for advanced planning and resolution.
  - Complex multi-page workflows with aggressive CAPTCHAs can require manual user intervention.

## 7. How can another developer run or extend it?
**To Run:**
1. Start the FastAPI backend:
   ```bash
   cd RaspberryPiBackend
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. Start the Plasmo extension dev server:
   ```bash
   cd "Voice Agent"
   npm install
   npm run dev
   ```
3. Load unpacked extension in Chrome (`chrome://extensions/` -> `build/chrome-mv3-dev`).
4. Test hardware/Postman endpoints using the included `RaspberryPiBackend/postman.json` collection!

**To Extend:**
- **Add New Voice Endpoints:** Modify `app/routers/voice.py` in `RaspberryPiBackend`.
- **Add New Intents:** Modify `src/orchestration/intent/RuleBasedIntentExtractor.ts` in `Voice Agent`.
- **Improve AI Planning:** Enhance `src/orchestration/planner/AIPlanner.ts` by integrating new LLM providers or prompt chains.
- **New Element Resolvers:** Add custom computer vision or DOM traversal strategies inside `src/automation/resolver/`.
