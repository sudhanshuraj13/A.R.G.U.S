# ARGUS

ARGUS is a production-oriented MVP architecture for a voice-first AI browser automation assistant.

It separates UI, voice capture, intent extraction, LangGraph orchestration, deterministic safety checks, semantic element resolution, Playwright-like execution, validation, recovery, and TinyFish retrieval adapters into a clean, typed architecture.

## Overview

ARGUS allows users to navigate the web, fill forms, and automate tasks using natural language voice commands. It intercepts potentially dangerous actions (like purchases or security changes) and prompts for approval via a sleek Chrome Side Panel UI.

For a detailed breakdown of how ARGUS works, the architecture, challenges solved, and current status, please read the [**Technical Report**](./TECHNICAL_REPORT.md).

## Quick Start

1. Install dependencies:
   ```bash
   npm install
   ```
2. Start the Plasmo development server:
   ```bash
   npm run dev
   ```
3. Load the unpacked extension in Chrome:
   - Go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `build/chrome-mv3-dev` directory.

## Core Commands

```bash
npm run typecheck    # Run TypeScript type checking
npm run build        # Build the production extension
npm run lint         # Run ESLint
```

## Architecture

The frontend UI handles the voice bubble, sidebar state, approvals, notifications, and settings. Browser automation planning and execution live in typed services under `src/orchestration`, `src/safety`, `src/automation`, and `src/tinyfish`. 

The system leverages a Custom DOM Runtime injected via Content Scripts to execute actions natively, bypassing Chrome Extension sandbox limitations while maintaining a Playwright-like abstraction.
