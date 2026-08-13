"""
ARGUS Memory Module
Manages conversation history and persistent notes storage.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

from config import MAX_CONVERSATION_HISTORY, NOTES_FILE


class MemoryManager:
    """Handles short-term conversation memory and persistent note storage."""

    def __init__(
        self,
        max_history: int = MAX_CONVERSATION_HISTORY,
        notes_file: str = NOTES_FILE,
    ):
        self.max_history = max_history
        self.notes_file = notes_file
        self.conversation_history: List[Dict[str, str]] = []
        self.notes: List[Dict[str, str]] = self._load_notes()

    # ── Conversation History ─────────────────────────────

    def add_interaction(self, user_input: str, assistant_response: str) -> None:
        """Record a user–assistant exchange in short-term memory."""
        timestamp = datetime.now().isoformat()
        self.conversation_history.append(
            {"role": "user", "content": user_input, "timestamp": timestamp}
        )
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_response, "timestamp": timestamp}
        )
        # Keep only the last N exchanges (each exchange = 2 messages)
        max_messages = self.max_history * 2
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]

    def get_history(self) -> List[Dict[str, str]]:
        """Return the current conversation history."""
        return list(self.conversation_history)

    def get_history_as_text(self) -> str:
        """Return conversation history formatted as readable text."""
        if not self.conversation_history:
            return ""
        lines = []
        for msg in self.conversation_history:
            role = "User" if msg["role"] == "user" else "ARGUS"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def clear_history(self) -> None:
        """Clear all conversation history."""
        self.conversation_history = []

    # ── Notes Management ─────────────────────────────────

    def add_note(self, note_text: str) -> Dict[str, str]:
        """Save a new note with timestamp."""
        note = {
            "text": note_text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.notes.append(note)
        self._save_notes()
        return note

    def get_notes(self) -> List[Dict[str, str]]:
        """Return all saved notes."""
        return list(self.notes)

    def clear_notes(self) -> None:
        """Delete all notes from memory and disk."""
        self.notes = []
        self._save_notes()

    def clear_all(self) -> None:
        """Clear both conversation history and notes."""
        self.clear_history()
        self.clear_notes()

    # ── Persistence ──────────────────────────────────────

    def _load_notes(self) -> List[Dict[str, str]]:
        """Load notes from the JSON file on disk."""
        if os.path.exists(self.notes_file):
            try:
                with open(self.notes_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_notes(self) -> None:
        """Persist notes to the JSON file on disk."""
        try:
            with open(self.notes_file, "w", encoding="utf-8") as f:
                json.dump(self.notes, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[MemoryManager] Warning: Could not save notes — {e}")
