"""
ARGUS Multi-Agent StateGraph powered by LangGraph.

Architecture:
               ┌─────────────────────────┐
               │       START NODE        │
               └────────────┬────────────┘
                            │
                            ▼
               ┌─────────────────────────┐
               │    SUPERVISOR NODE      │
               │  (Intent Classifier)    │
               └────────────┬────────────┘
                            │
                  [Conditional Router]
      ┌───────────┬─────────┼─────────┬───────────┬───────────┐
      │ (scene)   │ (curr)  │ (ocr)   │ (obj)     │ (general) │ (tools)
      ▼           ▼         ▼         ▼           ▼           ▼
 ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
 │ VISION  │ │CURRENCY │ │   OCR   │ │ OBJECT  │ │ CONVERS.│ │  TOOLS  │
 │ AGENT   │ │ AGENT   │ │ AGENT   │ │ AGENT   │ │  AGENT  │ │  NODE   │
 └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
      │           │           │           │           │           │
      └───────────┴───────────┼───────────┴───────────┴───────────┘
                              ▼
                     ┌─────────────────┐
                     │    END NODE     │
                     └─────────────────┘
"""

from typing import TypedDict, Optional, List, Dict, Any
from PIL import Image
from langgraph.graph import StateGraph, END

# ── State Schema Definition ──────────────────────────
class ARGUSState(TypedDict):
    user_query: str
    intent: str
    pil_image: Optional[Image.Image]
    response: str
    history: List[Dict[str, Any]]
    error: Optional[str]


def safe_print(msg: str) -> None:
    """Print message safely on Windows terminals without UnicodeEncodeError."""
    try:
        print(msg)
    except UnicodeEncodeError:
        clean_msg = msg.encode("ascii", "ignore").decode("ascii")
        print(clean_msg)


def build_argus_graph(assistant_engine):
    """
    Builds and compiles the LangGraph StateGraph for ARGUS.
    Takes an AssistantEngine instance for executing node logic.
    """
    builder = StateGraph(ARGUSState)

    # ── Node 1: Supervisor Node ──────────────────────
    def supervisor_node(state: ARGUSState) -> Dict[str, Any]:
        query = state.get("user_query", "").strip()
        intent = assistant_engine.classify_intent(query)
        safe_print(f"  [LangGraph Supervisor] Classified intent -> '{intent}'")
        return {"intent": intent}

    # ── Node 2: Conversational Agent Node ─────────────
    def conversational_agent_node(state: ARGUSState) -> Dict[str, Any]:
        query = state.get("user_query", "")
        safe_print("  [LangGraph Conversational Subagent] Generating response...")
        response, intent, extra = assistant_engine._handle_general(query)
        return {"response": response, "pil_image": None}

    # ── Node 3: Vision Agent Node (Scene) ────────────
    def vision_agent_node(state: ARGUSState) -> Dict[str, Any]:
        query = state.get("user_query", "")
        safe_print("  [LangGraph Scene Subagent] Analyzing scene description...")
        response, intent, extra = assistant_engine._handle_scene(query)
        return {"response": response, "pil_image": extra}

    # ── Node 4: Currency Subagent Node ───────────────
    def currency_agent_node(state: ARGUSState) -> Dict[str, Any]:
        query = state.get("user_query", "")
        safe_print("  [LangGraph Currency Subagent] Detecting Indian currency notes/coins...")
        response, intent, extra = assistant_engine._handle_currency(query)
        return {"response": response, "pil_image": extra}

    # ── Node 5: OCR Subagent Node ─────────────────────
    def ocr_agent_node(state: ARGUSState) -> Dict[str, Any]:
        query = state.get("user_query", "")
        safe_print("  [LangGraph OCR Subagent] Reading text from frame...")
        response, intent, extra = assistant_engine._handle_ocr(query)
        return {"response": response, "pil_image": extra}

    # ── Node 6: Object Location Subagent Node ─────────
    def object_agent_node(state: ARGUSState) -> Dict[str, Any]:
        query = state.get("user_query", "")
        safe_print("  [LangGraph Object Subagent] Detecting objects & spatial locations...")
        response, intent, extra = assistant_engine._handle_object(query)
        return {"response": response, "pil_image": extra}

    # ── Node 7: Tools Node (Notes / Time / Date) ──────
    def tools_node(state: ARGUSState) -> Dict[str, Any]:
        query = state.get("user_query", "")
        intent = state.get("intent", "general")
        safe_print(f"  [LangGraph Tools Subagent] Executing action -> '{intent}'")

        if intent == "note":
            response, _, _ = assistant_engine._handle_note(query)
        elif intent == "time":
            response, _, _ = assistant_engine._handle_time(query)
        elif intent == "date":
            response, _, _ = assistant_engine._handle_date(query)
        else:
            response = "Action completed."

        return {"response": response, "pil_image": None}

    # ── Conditional Router Edge Function ─────────────
    def router_edge(state: ARGUSState) -> str:
        intent = state.get("intent", "general")
        if intent == "currency":
            return "currency_agent"
        elif intent == "ocr":
            return "ocr_agent"
        elif intent == "object":
            return "object_agent"
        elif intent == "scene":
            return "vision_agent"
        elif intent in ["note", "time", "date"]:
            return "tools_node"
        else:
            return "conversational_agent"

    # ── Add Nodes ────────────────────────────────────
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("conversational_agent", conversational_agent_node)
    builder.add_node("vision_agent", vision_agent_node)
    builder.add_node("currency_agent", currency_agent_node)
    builder.add_node("ocr_agent", ocr_agent_node)
    builder.add_node("object_agent", object_agent_node)
    builder.add_node("tools_node", tools_node)

    # ── Add Edges ────────────────────────────────────
    builder.set_entry_point("supervisor")

    builder.add_conditional_edges(
        "supervisor",
        router_edge,
        {
            "vision_agent": "vision_agent",
            "currency_agent": "currency_agent",
            "ocr_agent": "ocr_agent",
            "object_agent": "object_agent",
            "conversational_agent": "conversational_agent",
            "tools_node": "tools_node",
        }
    )

    builder.add_edge("conversational_agent", END)
    builder.add_edge("vision_agent", END)
    builder.add_edge("currency_agent", END)
    builder.add_edge("ocr_agent", END)
    builder.add_edge("object_agent", END)
    builder.add_edge("tools_node", END)

    # Compile StateGraph
    return builder.compile()

