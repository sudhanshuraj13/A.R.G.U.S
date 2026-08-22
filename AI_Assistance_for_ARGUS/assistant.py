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
    OCR_KEYWORDS = [
        "what is written", "what is writing", "what's written", "written on", "writing on",
        "read text", "read this", "read signboard", "signboard", "read sign", "read label",
        "what does it say", "read document", "read paper", "read words", "read text on",
        "read what", "what text",
    ]
    CURRENCY_KEYWORDS = [
        "currency", "rupee", "rupees", "cash", "banknote", "bank note",
        "currency note", "rupee note", "coin", "how much money", "which note",
        "what note", "what coin", "bill", "value of note", "value of this note",
        "note am i holding", "note in my hand", "holding note", "holding a note",
        "how many notes", "many notes", "dominion note", "denomination", "denominations",
        "notes am i", "how many rupee", "what currency", "currency i am holding",
    ]
    NOTE_KEYWORDS = [
        "take a note", "note down", "save a note", "make a note",
        "remember that", "remember to", "remind me", "write down",
        "jot down", "record that", "save that", "meeting at", "appointment",
        "my saved notes", "read my notes", "what are my notes", "list my notes",
        "show my notes", "my reminders", "what notes do i have",
    ]
    OBJECT_KEYWORDS = [
        "find object", "find my", "where is", "locate", "object detection",
        "detect objects", "what objects", "what object", "where is the",
        "what am i holding", "what is in my hand", "what's in my hand",
        "holding in my hand", "what do i have", "identify this", "identify object",
        "what is this object", "what's this object", "tell me what object",
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
        Classify user query into one of: ocr, currency, note, object, scene, time, date, general.
        Evaluates OCR and Currency before saved memory notes to respect Indian context ('note' = currency bill / written text).
        """
        q = query.lower().strip()

        # 1. OCR (Reading physical text/writing via camera)
        for keyword in self.OCR_KEYWORDS:
            if keyword in q:
                return "ocr"

        # 2. Currency (Indian banknotes ₹10-₹500 & coins)
        for keyword in self.CURRENCY_KEYWORDS:
            if keyword in q:
                return "currency"

        # 3. Note/Task Memory (Saving/fetching text reminders)
        for keyword in self.NOTE_KEYWORDS:
            if keyword in q:
                return "note"

        # 4. Object Detection & Spatial Location
        for keyword in self.OBJECT_KEYWORDS:
            if keyword in q:
                return "object"

        # 5. Scene Understanding
        for keyword in self.SCENE_KEYWORDS:
            if keyword in q:
                return "scene"

        # 6. Time & Date
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

            # Safety Refusal Fallback: If VLM triggered a false-positive guardrail, read printed note text
            refusal_triggers = ["can't assist", "cannot assist", "can't help", "cannot help", "sorry, but i can't"]
            if any(trig in description.lower() for trig in refusal_triggers) and pil_image is not None:
                ocr_desc, _ = self.vision.read_text_ocr("Read the banknote number and denomination value on this note", frame=pil_image)
                if ocr_desc and not any(trig in ocr_desc.lower() for trig in refusal_triggers):
                    description = ocr_desc

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
