import glob as _glob_mod
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from base import BaseAgent
from health_agent import ScraperHealthAgent
from articles_agent import ArticlesAgent
from listings_agent import ListingsAgent
from standardize_agent import StandardizationAgent
from cleaning_agent import CleaningAgent
from quality_agent import QualityGuardAgent
from llm import LLM_PRIMARY, LLM_FALLBACK, call_llm, parse_llm_json
from memory_store import HEURISTICS, HEURISTICS_PATH


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


class OrchestratorAgent(BaseAgent):
    """
    Master controller — sequences all agents, uses LLM for stage gate decisions.
    Stage 0: ScraperHealthAgent (pre-flight)
    Stage 1: ArticlesAgent
    Stage 2: ListingsAgent
    Stage 3: StandardizationAgent
    Stage 4: CleaningAgent
    Stage 5: QualityGuardAgent
    """

    MIN_LISTINGS           = 500
    DECISION_MODEL_ROUTINE = LLM_PRIMARY
    DECISION_MODEL_COMPLEX = LLM_FALLBACK

    def __init__(self):
        super().__init__("OrchestratorAgent")
        self.health_agent          = ScraperHealthAgent()
        self.articles_agent        = ArticlesAgent()
        self.listings_agent        = ListingsAgent()
        self.standardization_agent = StandardizationAgent()
        self.cleaning_agent        = CleaningAgent()
        self.quality_agent         = QualityGuardAgent()

    def run(self, state: Dict[str, Any] = None) -> Dict[str, Any]:
        state = state or {
            "run_id":          datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            "started_at":      datetime.utcnow().isoformat() + "Z",
            "pipeline_status": "running",
        }

        self.log.info("=" * 60)
        self.log.info("  LENS ESTATE PIPELINE — ORCHESTRATOR")
        self.log.info(f"  Run ID  : {state['run_id']}")
        self.log.info(f"  Started : {state['started_at']}")
        self.log.info("=" * 60)

        # Stage 0: Health
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 0 — Scraper Health Checks")
        self.log.info("█" * 60)
        state   = self.health_agent.run(state)
        health  = state.get("scraper_health", {})
        blocked = [n for n, h in health.items() if h.get("status") == "blocked"]
        down    = [n for n, h in health.items() if h.get("status") == "down"]
        if blocked: self.log.warning(f"  Sites BLOCKED: {blocked}")
        if down:    self.log.warning(f"  Sites DOWN: {down}")

        # Stage 1: Articles
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 1 — Articles Collection")
        self.log.info("█" * 60)
        state     = self.articles_agent.run(state)
        art_paths = state.get("articles_raw_paths", [])
        self.log.info(f"Articles stage complete: {len(art_paths)} sources")

        # Stage 2: Listings
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 2 — Listings Collection")
        self.log.info("█" * 60)
        state = self.listings_agent.run(state)
        dec   = self._decide("listings_collection", state)
        self.log_decision(dec, "after_listings")
        if dec["action"] == "abort":
            return self._abort(state, dec["reason"])

        # Stage 3: Standardization
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 3 — Standardization")
        self.log.info("█" * 60)
        state = self.standardization_agent.run(state)
        dec   = self._decide("standardization", state)
        self.log_decision(dec, "after_standardization")
        if dec["action"] == "abort":
            return self._abort(state, dec["reason"])
        if dec["action"] == "retry":
            self.log.info("Orchestrator ordered RETRY on standardization")
            state = self.standardization_agent.run(state)

        # Stage 4: Cleaning
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 4 — Cleaning")
        self.log.info("█" * 60)
        state = self.cleaning_agent.run(state)
        dec   = self._decide("cleaning", state)
        self.log_decision(dec, "after_cleaning")
        if dec["action"] == "abort":
            return self._abort(state, dec["reason"])

        # Stage 5: Quality Guard
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 5 — Quality Guard")
        self.log.info("█" * 60)
        state = self.quality_agent.run(state)

        self._save_report(state)
        rows = state.get("final_row_count", 0)
        self.log.info("\n" + "=" * 60)
        self.log.info(f"  PIPELINE COMPLETE — {state.get('pipeline_status','?').upper()}")
        self.log.info(f"  Final rows : {rows:,}")
        self.log.info(f"  Output     : {state.get('model_ready_path', 'N/A')}")
        self.log.info(f"  Quality    : {state.get('quality_score', 'N/A')}/100")
        self.log.info(f"  Report     : logs/run_{state['run_id']}.json")
        self.log.info("=" * 60)
        return state

    def _decide(self, stage: str, state: Dict) -> Dict:
        ctx: Dict[str, Any] = {
            "stage":           stage,
            "run_id":          state.get("run_id"),
            "min_rows_target": self.MIN_LISTINGS,
        }

        if stage == "listings_collection":
            results = state.get("listings_results", {})
            ctx.update({
                "total_rows_collected":  state.get("listings_total_rows", 0),
                "has_synthetic_data":    state.get("listings_has_synthetic", False),
                "scraper_health":        state.get("scraper_health", {}),
                "health_summary":        state.get("scraper_health_summary", ""),
                "sources": {
                    name: {
                        "status":        r.get("status"),
                        "rows":          r.get("rows", 0),
                        "fallback_rung": r.get("fallback_rung", ""),
                    }
                    for name, r in results.items()
                },
                "sources_succeeded": sum(1 for r in results.values() if r.get("status") == "success"),
                "sources_fallback":  sum(1 for r in results.values() if r.get("status") == "fallback"),
                "sources_failed":    sum(1 for r in results.values() if r.get("status") == "failed"),
                "recent_failures":   self.listings_agent.memory.recall("failures", 10),
            })

        elif stage == "standardization":
            ctx.update({
                "standardization_status": state.get("standardization_status"),
                "standardization_report": state.get("standardization_report", {}),
                "listings_total_rows":    state.get("listings_total_rows", 0),
                "has_synthetic_data":     state.get("listings_has_synthetic", False),
            })

        elif stage == "cleaning":
            cleaning_report = state.get("cleaning_report", {})
            ctx.update({
                "cleaning_status":    state.get("cleaning_status"),
                "final_row_count":    state.get("final_row_count", 0),
                "cleaning_report":    cleaning_report,
                "suspicious_count":   cleaning_report.get("suspicious", 0),
                "null_rate":          cleaning_report.get("null_rate", {}),
                "has_synthetic_data": state.get("listings_has_synthetic", False),
            })

        rows_ok    = ctx.get("total_rows_collected", ctx.get("final_row_count", 1)) > 0
        all_failed = ctx.get("sources_failed", 0) >= len(ctx.get("sources", {"x": 1}))
        model      = self.DECISION_MODEL_COMPLEX if (not rows_ok or all_failed) \
                     else self.DECISION_MODEL_ROUTINE

        prompt = self._build_decision_prompt(stage, ctx)
        self.log.info(f"\nAsking LLM for routing decision after: {stage} (model={model})")
        result = self.decide(prompt, context=ctx, model=model)

        valid_actions = {"continue", "retry", "abort", "accept_degraded"}
        if result.get("action") not in valid_actions:
            self.log.warning(f"Invalid LLM action '{result.get('action')}' — defaulting to continue")
            result = {
                "thought":    "Invalid action returned — defaulting to continue safely.",
                "action":     "continue",
                "reason":     "invalid_llm_output",
                "confidence": 0.3,
            }
        return result

    def _build_decision_prompt(self, stage: str, ctx: Dict) -> str:
        schema = (
            'Return ONLY this JSON:\n'
            '{\n'
            '  "thought": "<step-by-step reasoning referencing specific numbers>",\n'
            '  "action":  "<continue | retry | abort | accept_degraded>",\n'
            '  "reason":  "<one sentence>",\n'
            '  "confidence": <0.0–1.0>\n'
            '}'
        )
        action_guide = (
            "Action rules:\n"
            "  continue        — data sufficient, proceed\n"
            "  retry           — borderline, worth one more attempt\n"
            "  abort           — unrecoverable (0 real rows, critical error)\n"
            "  accept_degraded — below target but usable\n"
            f"  Minimum acceptable rows: {self.MIN_LISTINGS:,}\n"
        )

        if stage == "listings_collection":
            return (
                f"Stage 'listings_collection' finished.\n\n{action_guide}\n"
                f"Guidance:\n"
                f"  - rows >= {self.MIN_LISTINGS} from real scrapers → continue\n"
                f"  - rows 200–{self.MIN_LISTINGS-1} with >= 1 real source → accept_degraded\n"
                f"  - all sources failed/fallback and 0 real rows → abort\n\n"
                f"{schema}"
            )
        elif stage == "standardization":
            return (
                f"Stage 'standardization' finished.\n\n{action_guide}\n"
                f"Guidance:\n"
                f"  - status=success and rows > {self.MIN_LISTINGS} → continue\n"
                f"  - status=failed → retry once, then abort\n\n"
                f"{schema}"
            )
        elif stage == "cleaning":
            return (
                f"Stage 'cleaning' finished.\n\n{action_guide}\n"
                f"Guidance:\n"
                f"  - final_row_count >= {self.MIN_LISTINGS} → continue\n"
                f"  - 200–{self.MIN_LISTINGS-1} → accept_degraded\n"
                f"  - < 200 → abort\n\n"
                f"{schema}"
            )
        return f"Stage '{stage}' finished. Decide next action.\n\n{action_guide}\n{schema}"

    def _abort(self, state: Dict, reason: str) -> Dict:
        self.log.error(f"PIPELINE ABORTED: {reason}")
        state["pipeline_status"] = "aborted"
        state["abort_reason"]    = reason
        self.memory.remember("failures", {"reason": reason, "ts": _now()})
        self._save_report(state)
        return state

    def _save_report(self, state: Dict):
        report = {
            "run_id":          state.get("run_id"),
            "started_at":      state.get("started_at"),
            "completed_at":    _now(),
            "pipeline_status": state.get("pipeline_status"),
            "final_row_count": state.get("final_row_count", 0),
            "has_synthetic":   state.get("listings_has_synthetic", False),
            "model_ready":     state.get("model_ready_path", ""),
            "quality_score":   state.get("quality_score", None),
            "quality_notes":   state.get("quality_notes", ""),
            "scraper_health":  state.get("scraper_health", {}),
            "health_summary":  state.get("scraper_health_summary", ""),
            "articles":        state.get("articles_results", {}),
            "listings":        state.get("listings_results", {}),
            "std_report":      state.get("standardization_report", {}),
            "cleaning_report": state.get("cleaning_report", {}),
            "llm_decisions":   self.memory.recall("decisions", 20),
        }
        path = f"logs/run_{state.get('run_id', 'unknown')}.json"
        Path("logs").mkdir(exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        self.log.info(f"Run report saved → {path}")


# ── Weekly heuristic review ───────────────────────────────────────────────────

def run_weekly_review(
    min_runs:           int  = 5,
    max_runs_to_review: int  = 30,
    dry_run:            bool = False,
) -> List[Dict]:
    """
    Read the last N run reports from logs/run_*.json and ask the LLM to
    distil patterns into new heuristics.
    Call this manually after accumulating enough run history.
    """
    from llm import _build_logger as _bl
    log = _bl("WeeklyReview")
    log.info("=" * 60)
    log.info("  WEEKLY HEURISTIC REVIEW")
    log.info("=" * 60)

    report_files = sorted(
        _glob_mod.glob("logs/run_*.json"),
        key=os.path.getmtime,
        reverse=True,
    )[:max_runs_to_review]

    if len(report_files) < min_runs:
        log.warning(f"Only {len(report_files)} run reports found — need {min_runs} minimum.")
        return []

    log.info(f"Reviewing {len(report_files)} run reports...")

    reports = []
    for path in report_files:
        try:
            with open(path, encoding="utf-8") as f:
                reports.append(json.load(f))
        except Exception as e:
            log.warning(f"Could not read {path}: {e}")

    summaries = []
    for r in reports:
        listings     = r.get("listings", {})
        src_summary  = {
            name: {"status": v.get("status"), "rows": v.get("rows", 0), "fallback_rung": v.get("fallback_rung", "")}
            for name, v in listings.items()
        }
        health         = r.get("scraper_health", {})
        health_summary = {name: h.get("status") for name, h in health.items()}
        decisions      = r.get("llm_decisions", [])
        decision_actions = [d.get("decision", {}).get("action") for d in decisions if d.get("decision")]

        summaries.append({
            "run_id":        r.get("run_id", "?"),
            "status":        r.get("pipeline_status", "?"),
            "final_rows":    r.get("final_row_count", 0),
            "has_synthetic": r.get("has_synthetic", False),
            "listings":      src_summary,
            "health":        health_summary,
            "decisions":     decision_actions,
        })

    existing_rules = [h["rule"] for h in HEURISTICS.get_all()]

    prompt = (
        f"You are reviewing {len(summaries)} pipeline run reports for LensEstate.\n\n"
        f"RUN HISTORY (most recent first):\n{json.dumps(summaries, indent=2)}\n\n"
        f"EXISTING HEURISTICS (do not duplicate):\n{json.dumps(existing_rules, indent=2)}\n\n"
        f"Identify 3–6 NEW durable patterns that should guide future agent decisions.\n\n"
        f"Return ONLY this JSON:\n"
        f"{{\n"
        f'  "thought": "your overall analysis",\n'
        f'  "heuristics": [\n'
        f'    {{\n'
        f'      "scope": "mubawab | tayara | tunisie_annonce | bnb | houni | global",\n'
        f'      "rule": "concrete actionable rule in plain English",\n'
        f'      "confidence": 0.0-1.0,\n'
        f'      "applies_to": ["ListingsAgent", "ArticlesAgent", "OrchestratorAgent"]\n'
        f'    }}\n'
        f'  ]\n'
        f"}}"
    )

    log.info("Calling LLM for heuristic distillation...")
    raw    = call_llm(prompt, model=LLM_FALLBACK, max_tokens=1024)
    result = parse_llm_json(raw)

    thought    = result.get("thought", "")
    heuristics = result.get("heuristics", [])

    log.info(f"\nLLM analysis:\n  {thought[:400]}")
    log.info(f"\nProposed heuristics: {len(heuristics)}")

    added = []
    for h in heuristics:
        scope      = h.get("scope", "global")
        rule       = h.get("rule", "").strip()
        confidence = float(h.get("confidence", 0.75))
        applies_to = h.get("applies_to", ["global"])

        if not rule:
            continue

        log.info(f"\n  scope={scope}  confidence={confidence:.2f}")
        log.info(f"  rule: {rule}")

        if dry_run:
            log.info("  [DRY RUN — not saved]")
            added.append({"scope": scope, "rule": rule, "confidence": confidence, "applies_to": applies_to, "dry_run": True})
        else:
            entry = HEURISTICS.add(
                scope=scope, rule=rule, confidence=confidence,
                applies_to=applies_to,
                source=f"review_{datetime.utcnow().strftime('%Y%m%d')}",
            )
            added.append(entry)

    if not dry_run and added:
        log.info(f"\n✅ {len(added)} new heuristics saved to {HEURISTICS_PATH}")
    elif dry_run:
        log.info(f"\n[DRY RUN] Would have added {len(added)} heuristics")

    return added


if __name__ == "__main__":
    import sys

    if "--review" in sys.argv:
        run_weekly_review()
    else:
        agent = OrchestratorAgent()
        agent.run()

