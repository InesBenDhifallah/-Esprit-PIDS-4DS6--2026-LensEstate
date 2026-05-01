# ─────────────────────────────────────────────────────────────────────────────
# CELL 118 — OrchestratorAgent  (Phase 1 + Phase 3 combined — full replacement)
# ─────────────────────────────────────────────────────────────────────────────

class OrchestratorAgent(BaseAgent):
    """
    Master controller — sequences all agents, uses LLM for stage gate decisions.

    Phase 3 addition: ScraperHealthAgent runs as Stage 0 (pre-flight)
    before any scraper is touched. Its results flow into ListingsAgent's
    ReAct loop and inform the LLM's routing decisions.
    """

    MIN_LISTINGS = 500

    DECISION_MODEL_ROUTINE = LLM_PRIMARY
    DECISION_MODEL_COMPLEX = LLM_FALLBACK

    def __init__(self):
        super().__init__("OrchestratorAgent")
        self.health_agent          = ScraperHealthAgent()
        self.articles_agent        = ArticlesAgent()
        self.listings_agent        = ListingsAgent()
        self.standardization_agent = StandardizationAgent()
        self.cleaning_agent        = CleaningAgent()

    # ── Main pipeline ──────────────────────────────────────────────────────────
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

        # ── STAGE 0: Pre-flight health checks (Phase 3) ───────────────────────
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 0 — Scraper Health Checks")
        self.log.info("█" * 60)
        state = self.health_agent.run(state)
        health = state.get("scraper_health", {})
        blocked = [n for n, h in health.items() if h.get("status") == "blocked"]
        down    = [n for n, h in health.items() if h.get("status") == "down"]
        if blocked:
            self.log.warning(f"  Sites BLOCKED (IP block/rate limit): {blocked}")
        if down:
            self.log.warning(f"  Sites DOWN: {down}")

        # ── STAGE 1: Articles ─────────────────────────────────────────────────
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 1 — Articles Collection")
        self.log.info("█" * 60)
        state     = self.articles_agent.run(state)
        art_paths = state.get("articles_raw_paths", [])
        self.log.info(f"Articles stage complete: {len(art_paths)} sources")

        # ── STAGE 2: Listings ─────────────────────────────────────────────────
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 2 — Listings Collection")
        self.log.info("█" * 60)
        state = self.listings_agent.run(state)
        dec   = self._decide("listings_collection", state)
        self.log_decision(dec, "after_listings")
        if dec["action"] == "abort":
            return self._abort(state, dec["reason"])

        # ── STAGE 3: Standardization ──────────────────────────────────────────
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

        # ── STAGE 4: Cleaning ─────────────────────────────────────────────────
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 4 — Cleaning")
        self.log.info("█" * 60)
        state = self.cleaning_agent.run(state)
        dec   = self._decide("cleaning", state)
        self.log_decision(dec, "after_cleaning")
        if dec["action"] == "abort":
            return self._abort(state, dec["reason"])

        # ── STAGE 5: Final Validation ─────────────────────────────────────────
        self.log.info("\n" + "█" * 60)
        self.log.info("  STAGE 5 — Final Validation")
        self.log.info("█" * 60)
        rows       = state.get("final_row_count", 0)
        has_synth  = state.get("listings_has_synthetic", False)

        if rows >= self.MIN_LISTINGS and not has_synth:
            state["pipeline_status"] = "success"
            self.log.info(f"✅ PIPELINE SUCCESS — {rows:,} model-ready rows")
        elif rows >= self.MIN_LISTINGS and has_synth:
            state["pipeline_status"] = "degraded_synthetic"
            self.log.warning(f"⚠️  PIPELINE DEGRADED (synthetic data) — {rows:,} rows")
        elif rows > 0:
            state["pipeline_status"] = "degraded"
            self.log.warning(f"⚠️  PIPELINE DEGRADED — {rows:,} rows (min {self.MIN_LISTINGS:,})")
        else:
            state["pipeline_status"] = "failed"
            self.log.error("❌ PIPELINE FAILED — 0 rows in final output")

        self._save_report(state)
        self.log.info("\n" + "=" * 60)
        self.log.info(f"  PIPELINE COMPLETE — {state['pipeline_status'].upper()}")
        self.log.info(f"  Final rows : {rows:,}")
        self.log.info(f"  Output     : {state.get('model_ready_path', 'N/A')}")
        self.log.info(f"  Report     : logs/run_{state['run_id']}.json")
        self.log.info("=" * 60)
        return state

    # ── Stage gate decision ────────────────────────────────────────────────────
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
                "cleaning_status":      state.get("cleaning_status"),
                "final_row_count":      state.get("final_row_count", 0),
                "cleaning_report":      cleaning_report,
                "suspicious_count":     cleaning_report.get("suspicious", 0),
                "duplicates_removed":   cleaning_report.get("duplicates_removed", 0),
                "null_rate":            cleaning_report.get("null_rate", {}),
                "has_synthetic_data":   state.get("listings_has_synthetic", False),
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
            "  NOTE: if has_synthetic_data=true, treat row count with caution — "
            "synthetic rows will be stripped before the model CSV.\n"
        )

        if stage == "listings_collection":
            return (
                f"Stage 'listings_collection' finished.\n\n{action_guide}\n"
                f"Guidance:\n"
                f"  - rows >= {self.MIN_LISTINGS} from real scrapers → continue\n"
                f"  - rows 200–{self.MIN_LISTINGS-1} with >= 1 real source → accept_degraded\n"
                f"  - all sources failed/fallback and 0 real rows → abort\n"
                f"  - blocked sites: note in thought but don't abort if cache provides data\n\n"
                f"{schema}"
            )
        elif stage == "standardization":
            return (
                f"Stage 'standardization' finished.\n\n{action_guide}\n"
                f"Guidance:\n"
                f"  - status=success and rows > {self.MIN_LISTINGS} → continue\n"
                f"  - status=failed → retry once, then abort\n"
                f"  - significant row drop → note but continue unless < 200 remain\n\n"
                f"{schema}"
            )
        elif stage == "cleaning":
            return (
                f"Stage 'cleaning' finished.\n\n{action_guide}\n"
                f"Guidance:\n"
                f"  - final_row_count >= {self.MIN_LISTINGS} → continue\n"
                f"  - 200–{self.MIN_LISTINGS-1} → accept_degraded\n"
                f"  - < 200 → abort\n"
                f"  - suspicious > 20% of rows → note but continue (they're tagged, not deleted)\n"
                f"  - high null_rate on price or surface_m2 (>40%) → note in thought\n\n"
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
            "run_id":           state.get("run_id"),
            "started_at":       state.get("started_at"),
            "completed_at":     _now(),
            "pipeline_status":  state.get("pipeline_status"),
            "final_row_count":  state.get("final_row_count", 0),
            "has_synthetic":    state.get("listings_has_synthetic", False),
            "model_ready":      state.get("model_ready_path", ""),
            "scraper_health":   state.get("scraper_health", {}),
            "health_summary":   state.get("scraper_health_summary", ""),
            "articles":         state.get("articles_results", {}),
            "listings":         state.get("listings_results", {}),
            "std_report":       state.get("standardization_report", {}),
            "cleaning_report":  state.get("cleaning_report", {}),
            "llm_decisions":    self.memory.recall("decisions", 20),
        }
        path = f"logs/run_{state.get('run_id', 'unknown')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        self.log.info(f"Run report saved → {path}")

print("✅ OrchestratorAgent defined (Phase 1 + Phase 3)")
