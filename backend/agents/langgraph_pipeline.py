"""
LangGraph pipeline — Phase 5 crash recovery + typed state.
Import this module only if you want LangGraph crash recovery.
Falls back gracefully if LangGraph is not installed.
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

LANGGRAPH_AVAILABLE = False
SqliteSaver = None

try:
    from langgraph.graph import StateGraph, END
    from typing import TypedDict, Literal
    LANGGRAPH_AVAILABLE = True

    _SQLITE_CANDIDATES = [
        ("langgraph_checkpoint_sqlite",       "SqliteSaver"),
        ("langgraph.checkpoint.sqlite",       "SqliteSaver"),
        ("langgraph.checkpoint.sqlite.sync",  "SqliteSaver"),
    ]

    import importlib as _il
    for _mod_path, _cls_name in _SQLITE_CANDIDATES:
        try:
            _mod = _il.import_module(_mod_path)
            _cls = getattr(_mod, _cls_name, None)
            if _cls is not None:
                SqliteSaver = _cls
                break
        except (ImportError, ModuleNotFoundError):
            continue

    if SqliteSaver is None:
        try:
            from langgraph.checkpoint.memory import MemorySaver
            SqliteSaver = MemorySaver
        except ImportError:
            SqliteSaver = None

except ImportError:
    LANGGRAPH_AVAILABLE = False


if LANGGRAPH_AVAILABLE:
    from orchestrator import OrchestratorAgent
    from health_agent import ScraperHealthAgent
    from articles_agent import ArticlesAgent
    from listings_agent import ListingsAgent
    from standardize_agent import StandardizationAgent
    from cleaning_agent import CleaningAgent
    from quality_agent import QualityGuardAgent
    from llm import _build_logger

    class PipelineState(TypedDict, total=False):
        run_id:                   str
        started_at:               str
        pipeline_status:          str
        abort_reason:             str
        scraper_health:           dict
        scraper_health_summary:   str
        articles_raw_paths:       list
        articles_results:         dict
        merged_articles_path:     str
        listings_raw_paths:       list
        listings_results:         dict
        listings_total_rows:      int
        listings_has_synthetic:   bool
        merged_listings_path:     str
        standardization_status:   str
        standardization_report:   dict
        standardization_retried:  bool
        model_ready_path:         str
        cleaning_status:          str
        cleaning_report:          dict
        final_row_count:          int
        quality_approved:         bool
        quality_score:            float
        quality_notes:            str
        quality_report:           dict
        _next_stage:              str

    # Agent singletons
    _health_agent  = ScraperHealthAgent()
    _articles_agent = ArticlesAgent()
    _listings_agent = ListingsAgent()
    _std_agent      = StandardizationAgent()
    _cleaning_agent = CleaningAgent()
    _quality_agent  = QualityGuardAgent()
    _orchestrator   = OrchestratorAgent()

    def node_health(state: PipelineState) -> PipelineState:
        _build_logger("Graph.health").info("█" * 60 + "\n  NODE: health")
        return dict(_health_agent.run(dict(state)))

    def node_articles(state: PipelineState) -> PipelineState:
        _build_logger("Graph.articles").info("█" * 60 + "\n  NODE: articles")
        return dict(_articles_agent.run(dict(state)))

    def node_listings(state: PipelineState) -> PipelineState:
        _build_logger("Graph.listings").info("█" * 60 + "\n  NODE: listings")
        return dict(_listings_agent.run(dict(state)))

    def node_route_listings(state: PipelineState) -> "Literal['standardization', 'abort']":
        dec = _orchestrator._decide("listings_collection", dict(state))
        _orchestrator.log_decision(dec, "after_listings")
        return "abort" if dec["action"] == "abort" else "standardization"

    def node_standardization(state: PipelineState) -> PipelineState:
        _build_logger("Graph.standardization").info("█" * 60 + "\n  NODE: standardization")
        return dict(_std_agent.run(dict(state)))

    def node_route_standardization(state: PipelineState) -> "Literal['cleaning', 'standardization', 'abort']":
        dec = _orchestrator._decide("standardization", dict(state))
        _orchestrator.log_decision(dec, "after_standardization")
        if dec["action"] == "abort":
            return "abort"
        if dec["action"] == "retry" and not state.get("standardization_retried", False):
            return "standardization"
        return "cleaning"

    def node_standardization_mark_retry(state: PipelineState) -> PipelineState:
        return {**state, "standardization_retried": True}

    def node_cleaning(state: PipelineState) -> PipelineState:
        _build_logger("Graph.cleaning").info("█" * 60 + "\n  NODE: cleaning")
        return dict(_cleaning_agent.run(dict(state)))

    def node_route_cleaning(state: PipelineState) -> "Literal['quality_guard', 'abort']":
        dec = _orchestrator._decide("cleaning", dict(state))
        _orchestrator.log_decision(dec, "after_cleaning")
        return "abort" if dec["action"] == "abort" else "quality_guard"

    def node_quality_guard(state: PipelineState) -> PipelineState:
        _build_logger("Graph.quality_guard").info("█" * 60 + "\n  NODE: quality_guard")
        result = _quality_agent.run(dict(state))
        _orchestrator._save_report(result)
        return result

    def node_abort(state: PipelineState) -> PipelineState:
        _build_logger("Graph.abort").error("PIPELINE ABORTED by LangGraph routing decision")
        result = dict(state)
        result["pipeline_status"] = "aborted"
        _orchestrator._save_report(result)
        return result

    def build_pipeline_graph(
        checkpoint_db:   str  = "memory/pipeline_runs.db",
        hitl_on_quality: bool = False,
    ) -> tuple:
        graph = StateGraph(PipelineState)

        graph.add_node("health",                node_health)
        graph.add_node("articles",              node_articles)
        graph.add_node("listings",              node_listings)
        graph.add_node("standardization",       node_standardization)
        graph.add_node("standardization_retry", node_standardization_mark_retry)
        graph.add_node("cleaning",              node_cleaning)
        graph.add_node("quality_guard",         node_quality_guard)
        graph.add_node("abort",                 node_abort)

        graph.set_entry_point("health")
        graph.add_edge("health",   "articles")
        graph.add_edge("articles", "listings")

        graph.add_conditional_edges(
            "listings", node_route_listings,
            {"standardization": "standardization", "abort": "abort"},
        )
        graph.add_conditional_edges(
            "standardization", node_route_standardization,
            {"cleaning": "cleaning", "standardization": "standardization_retry", "abort": "abort"},
        )
        graph.add_edge("standardization_retry", "standardization")
        graph.add_conditional_edges(
            "cleaning", node_route_cleaning,
            {"quality_guard": "quality_guard", "abort": "abort"},
        )
        graph.add_edge("quality_guard", END)
        graph.add_edge("abort",         END)

        Path(checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
        checkpointer = None
        if SqliteSaver is not None:
            try:
                conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
                checkpointer = SqliteSaver(conn)
            except Exception:
                pass

        interrupt_before  = ["quality_guard"] if hitl_on_quality else []
        _compile_kwargs   = {"interrupt_before": interrupt_before}
        if checkpointer is not None:
            _compile_kwargs["checkpointer"] = checkpointer

        app = graph.compile(**_compile_kwargs)
        _build_logger("Graph").info(
            f"Pipeline graph compiled — checkpointer={'enabled' if checkpointer else 'disabled'}  "
            f"hitl={'quality_guard' if hitl_on_quality else 'disabled'}"
        )
        return app, checkpointer

    def run_pipeline_graph(
        hitl_on_quality:  bool            = False,
        resume_thread_id: Optional[str]   = None,
    ) -> dict:
        log = _build_logger("PipelineRunner")
        app, _ = build_pipeline_graph(hitl_on_quality=hitl_on_quality)

        if resume_thread_id:
            thread_id = resume_thread_id
            log.info(f"Resuming run {thread_id} from checkpoint...")
            config = {"configurable": {"thread_id": thread_id}}
            result = app.invoke(None, config=config)
        else:
            run_id    = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            thread_id = run_id
            initial_state: PipelineState = {
                "run_id":          run_id,
                "started_at":      datetime.utcnow().isoformat() + "Z",
                "pipeline_status": "running",
            }
            log.info(f"Starting fresh run {run_id}...")
            config = {"configurable": {"thread_id": thread_id}}
            result = app.invoke(initial_state, config=config)

        if result is None:
            log.info(
                "\n" + "=" * 60 + "\n"
                "  PIPELINE PAUSED — human review required\n"
                f"  To approve and continue:\n"
                f"      run_pipeline_graph(resume_thread_id='{thread_id}')\n"
                "=" * 60
            )
            return {"pipeline_status": "paused_hitl", "thread_id": thread_id}

        return result
