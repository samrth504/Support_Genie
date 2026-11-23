"""Builds and compiles the SupportGenie LangGraph agent.

    START -> guard -> classify --(injection?)--> route
                         |                         ^
                         +--> retrieve -> draft ---+
    route --(no reasons)--> auto_reply   -> END
          --(any reason)--> human_review -> END     (pauses with interrupt() until staff decide)

The checkpointer saves the graph state after every step. With PostgreSQL (Neon) a paused
ticket survives server restarts and can be resumed hours later. Tests use an in-memory saver.
"""
import logging
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import AgentState
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _after_classify(state: AgentState) -> str:
    # Suspected prompt injection -> skip RAG + LLM entirely (saves a call, removes the risk)
    return "route" if state.get("injection_flag") else "retrieve"


def _after_route(state: AgentState) -> str:
    return state["decision"]


def build_graph(checkpointer):
    g = StateGraph(AgentState)
    g.add_node("guard", nodes.guard_node)
    g.add_node("classify", nodes.classify_node)
    g.add_node("retrieve", nodes.retrieve_node)
    g.add_node("draft", nodes.draft_node)
    g.add_node("route", nodes.route_node)
    g.add_node("auto_reply", nodes.auto_reply_node)
    g.add_node("human_review", nodes.human_review_node)

    g.add_edge(START, "guard")
    g.add_edge("guard", "classify")
    g.add_conditional_edges("classify", _after_classify, {"route": "route", "retrieve": "retrieve"})
    g.add_edge("retrieve", "draft")
    g.add_edge("draft", "route")
    g.add_conditional_edges("route", _after_route, {"auto_reply": "auto_reply", "human_review": "human_review"})
    g.add_edge("auto_reply", END)
    g.add_edge("human_review", END)
    return g.compile(checkpointer=checkpointer)


def _make_checkpointer():
    url = get_settings().database_url
    if url.startswith("postgresql"):
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        pool = ConnectionPool(
            conninfo=url.replace("postgresql+psycopg://", "postgresql://", 1),
            min_size=1,
            max_size=5,
            max_idle=300,
            check=ConnectionPool.check_connection,   # Neon closes idle connections -> re-check before use
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            open=True,
        )
        saver = PostgresSaver(pool)
        saver.setup()  # creates the checkpoint tables once (idempotent)
        logger.info("LangGraph checkpointer: PostgreSQL")
        return saver

    try:
        from langgraph.checkpoint.memory import InMemorySaver
    except ImportError:  # older langgraph
        from langgraph.checkpoint.memory import MemorySaver as InMemorySaver
    logger.info("LangGraph checkpointer: in-memory (tests only)")
    return InMemorySaver()


@lru_cache
def get_agent():
    """Compiled graph, built once per process."""
    return build_graph(_make_checkpointer())


def draw_mermaid() -> str:
    """Mermaid diagram of the graph (used for docs / the presentation)."""
    return build_graph(None).get_graph().draw_mermaid()
