"""
ARGUS Supervisor Agent Engine
Acts as the central Supervisor Agent routing user queries to specialized subagents:
  1. Vision Subagent       → ESP32-CAM + Llama 3.2 Vision (for scene/visual queries)
  2. Conversational Subagent → Llama 3.2 Text Instruct + Memory (for day-to-day chat, notes, time, date)
"""

import re
from datetime import datetime
from typing import Tuple, Optional

from openai import OpenAI

from config import (
    KIMI_API_KEY, KIMI_TEXT_MODEL, KIMI_BASE_URL,
    ASSISTANT_SYSTEM_PROMPT,
)
from memory import MemoryManager
from vision import VisionModule


class AssistantEngine:
    """
    Central intelligence module for ARGUS.
    Routes user queries to the appropriate handler based on intent.

    Text queries → Kimi K2 (chat)
    Vision queries → Kimi K2 (vision)
    """

    # Intent keywords for classification
    NOTE_KEYWORDS = [
        "take a note", "note down", "save a note", "make a note",
        "remember that", "remember to", "remember", "remind me", "write down",
        "jot down", "record that", "save that", "meeting at", "appointment",
    ]
    CURRENCY_KEYWORDS = [
        "currency", "money", "rupee", "rupees", "cash", "banknote", "bank note",
        "currency note", "rupee note", "coin", "how much money", "which note",
        "what note", "what coin", "bill",
    ]
    OCR_KEYWORDS = [
        "read text", "read this", "read signboard", "signboard", "read sign", "read label",
        "what does it say", "read document", "read paper", "read words", "read text on",
    ]
    OBJECT_KEYWORDS = [
        "find object", "find my", "where is", "locate", "object detection",
        "detect objects", "what objects", "where is the",
    ]
    SCENE_KEYWORDS = [
        "describe", "surroundings", "around me", "in front of me",
        "what do you see", "what can you see", "see anything",
        "look around", "scene", "environment", "what is ahead",
        "dangerous", "hazard", "obstacle", "navigate", "where am i",
    ]
    TIME_KEYWORDS = ["what time", "current time", "tell me the time", "what's the time"]
    DATE_KEYWORDS = ["what date", "today's date", "what day", "tell me the date", "what's the date", "today is", "date today", "date"]


    def __init__(
        self,
        memory: MemoryManager,
        vision: VisionModule,
        api_key: str = KIMI_API_KEY,
        model: str = KIMI_TEXT_MODEL,
        base_url: str = KIMI_BASE_URL,
    ):
        self.memory = memory
        self.vision = vision
        self.model = model

        # Initialize Kimi K2 client
        self.client = None
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key, base_url=base_url)
            except Exception as e:
                print(f"[AssistantEngine] Kimi K2 init failed: {e}")

        if not self.client:
            raise ValueError(
                "KIMI_API_KEY must be set for the assistant to work."
            )

        # Initialize LangGraph StateGraph
        try:
            from agent_graph import build_argus_graph
            self.graph = build_argus_graph(self)
        except Exception as e:
            print(f"[AssistantEngine] LangGraph init notice: {e}")
            self.graph = None

    # ── Intent Classification ────────────────────────────

    def classify_intent(self, query: str) -> str:
        """
        Classify user query into one of: note, currency, ocr, object, scene, time, date, general.
        Uses keyword matching for speed and reliability.
        """
        q = query.lower().strip()

        for keyword in self.NOTE_KEYWORDS:
            if keyword in q:
                return "note"
        for keyword in self.CURRENCY_KEYWORDS:
            if keyword in q:
                return "currency"
        for keyword in self.OCR_KEYWORDS:
            if keyword in q:
                return "ocr"
        for keyword in self.OBJECT_KEYWORDS:
            if keyword in q:
                return "object"
        for keyword in self.SCENE_KEYWORDS:
            if keyword in q:
                return "scene"
        for keyword in self.TIME_KEYWORDS:
            if keyword in q:
                return "time"
        for keyword in self.DATE_KEYWORDS:
            if keyword in q:
                return "date"

        return "general"



    # ── Supervisor Agent Routing (LangGraph) ──────────────

    def process(self, query: str) -> Tuple[str, str, Optional[object]]:
        """
        Supervisor Agent main entry point:
        Executes query through the LangGraph StateGraph workflow.

        Returns:
            Tuple of (response_text, intent_type, extra_data).
        """
        if not query or not query.strip():
            return "I didn't catch that. Could you please repeat?", "empty", None

        # Execute through LangGraph StateGraph if available
        if self.graph:
            initial_state = {
                "user_query": query,
                "intent": "general",
                "pil_image": None,
                "response": "",
                "history": [],
                "error": None,
            }
            try:
                final_state = self.graph.invoke(initial_state)
                response = final_state.get("response", "")
                intent = final_state.get("intent", "general")
                pil_image = final_state.get("pil_image", None)
                return response, intent, pil_image
            except Exception as e:
                print(f"[LangGraph] Execution fallback: {e}")

        # Fallback direct routing
        intent = self.classify_intent(query)
        if intent == "currency":
            return self._handle_currency(query)
        elif intent == "ocr":
            return self._handle_ocr(query)
        elif intent == "object":
            return self._handle_object(query)
        elif intent == "scene":
            return self._handle_scene(query)
        elif intent == "note":
            return self._handle_note(query)
        elif intent == "time":
            return self._handle_time(query)
        elif intent == "date":
            return self._handle_date(query)
        else:
            return self._handle_general(query)


    # ── Text Generation ──────────────────────────────────

    def _generate_text(self, prompt: str) -> str:
        """Generate text using Kimi K2."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=40,
                temperature=0.5,
            )
            answer = response.choices[0].message.content.strip()
            if answer:
                return answer
        except Exception as e:
            print(f"[AssistantEngine] API text generation failed: {e}")
            return f"Error occurred: {str(e)}"

    # ── Intent Handlers ──────────────────────────────────

    def _handle_scene(self, query: str) -> Tuple[str, str, Optional[object]]:
        """Handle scene description requests via Kimi K2 Vision."""
        if not self.vision:
            return "Sorry, the camera system is not available right now.", "scene", None
        try:
            description, pil_image = self.vision.describe_with_question(query)
            self.memory.add_interaction(query, description)
            return description, "scene", pil_image
        except RuntimeError:
            return "Sorry, I can't access the camera right now. Please check the connection.", "scene", None
        except Exception as e:
            print(f"[AssistantEngine] Scene error: {e}")
            return f"Error occurred: {str(e)}", "scene", None

    def _handle_currency(self, query: str) -> Tuple[str, str, Optional[object]]:
        """Handle Indian currency detection subagent requests."""
        if not self.vision:
            return "Sorry, the camera system is not available right now.", "currency", None
        try:
            description, pil_image = self.vision.detect_currency(query)
            self.memory.add_interaction(query, description)
            return description, "currency", pil_image
        except RuntimeError:
            return "Sorry, I can't access the camera right now. Please check the connection.", "currency", None
        except Exception as e:
            print(f"[AssistantEngine] Currency detection error: {e}")
            return f"Error occurred: {str(e)}", "currency", None

    def _handle_ocr(self, query: str) -> Tuple[str, str, Optional[object]]:
        """Handle Text/OCR subagent requests."""
        if not self.vision:
            return "Sorry, the camera system is not available right now.", "ocr", None
        try:
            description, pil_image = self.vision.read_text_ocr(query)
            self.memory.add_interaction(query, description)
            return description, "ocr", pil_image
        except RuntimeError:
            return "Sorry, I can't access the camera right now. Please check the connection.", "ocr", None
        except Exception as e:
            print(f"[AssistantEngine] OCR error: {e}")
            return f"Error occurred: {str(e)}", "ocr", None

    def _handle_object(self, query: str) -> Tuple[str, str, Optional[object]]:
        """Handle Object Location Subagent requests."""
        if not self.vision:
            return "Sorry, the camera system is not available right now.", "object", None
        try:
            description, pil_image = self.vision.detect_objects(query)
            self.memory.add_interaction(query, description)
            return description, "object", pil_image
        except RuntimeError:
            return "Sorry, I can't access the camera right now. Please check the connection.", "object", None
        except Exception as e:
            print(f"[AssistantEngine] Object detection error: {e}")
            return f"Error occurred: {str(e)}", "object", None


    def _handle_note(self, query: str) -> Tuple[str, str, None]:
        """Handle note-taking requests."""
        note_content = self._extract_note_content(query)
        self.memory.add_note(note_content)
        response = f"Got it! I've saved your note: \"{note_content}\""
        self.memory.add_interaction(query, response)
        return response, "note", None

    def _handle_time(self, _query: str) -> Tuple[str, str, None]:
        """Handle time queries."""
        now = datetime.now()
        response = f"The current time is {now.strftime('%I:%M %p')}."
        self.memory.add_interaction("What time is it?", response)
        return response, "time", None

    def _handle_date(self, _query: str) -> Tuple[str, str, None]:
        """Handle date queries."""
        now = datetime.now()
        response = f"Today is {now.strftime('%A, %B %d, %Y')}."
        self.memory.add_interaction("What's the date?", response)
        return response, "date", None

    def _handle_general(self, query: str) -> Tuple[str, str, None]:
        """Handle general conversational queries via Kimi K2."""
        try:
            history_text = self.memory.get_history_as_text()
            context_block = (
                f"\n\nRecent conversation:\n{history_text}" if history_text else ""
            )

            prompt = (
                f"{context_block}\n\n"
                f"User: {query}\n"
                f"ARGUS:"
            )

            answer = self._generate_text(prompt)
            self.memory.add_interaction(query, answer)
            return answer, "general", None

        except Exception as e:
            print(f"[AssistantEngine] General handler error: {e}")
            return f"Error occurred: {str(e)}", "general", None

    # ── Utility ──────────────────────────────────────────

    @staticmethod
    def _extract_note_content(query: str) -> str:
        """Extract the actual note content from a note-taking command."""
        patterns = [
            r"(?:take a note|note down|save a note|make a note)\s*(?:saying|that|to)?\s+(.+)",
            r"(?:remember|remind me)\s*(?:that|to|about)?\s+(.+)",
            r"(?:write down|jot down|record)\s*(?:that)?\s+(.+)",
            r"(?:save)\s*(?:that)?\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip().rstrip(".")

        return query.strip().rstrip(".")
