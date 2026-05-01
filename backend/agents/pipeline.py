# ─────────────────────────────────────────────────────────────────────────────
# CELL 120 — Run the pipeline  (Phases 1-6)
# Prerequisite: set OPENROUTER_API_KEY before this cell.
# Quick sanity check: test_llm_connection()
#
# Two execution paths:
#   Path A (recommended) — LangGraph with crash recovery + QualityGuardAgent
#   Path B (legacy)      — OrchestratorAgent.run() + QualityGuardAgent
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(result: dict, mode: str = "LangGraph"):
    sep = "=" * 60
    print()
    print(sep)
    print(f"FINAL PIPELINE SUMMARY  ({mode})")
    print(sep)
    print("Status        :", result.get("pipeline_status", "?").upper())
    print("Run ID        :", result.get("run_id", "?"))
    print("Final rows    :", result.get("final_row_count", 0))
    print("Output        :", result.get("model_ready_path", "N/A"))
    print("Has synthetic :", result.get("listings_has_synthetic", False))

    qr = result.get("quality_report", {})
    if qr:
        print()
        print(f"Quality score : {qr.get('total_score', '?')}/100  "
              f"(threshold={qr.get('threshold', 60)})  "
              f"approved={'yes' if qr.get('approved') else 'no'}")
        print("Dimensions    :", {
            k: f"{v:.1f}" for k, v in qr.get("dimension_scores", {}).items()
        })
        if qr.get("narrative"):
            print("Narrative     :", qr["narrative"][:180])
        if qr.get("html_report"):
            print("HTML report   :", qr["html_report"])

    health = result.get("scraper_health", {})
    if health:
        print()
        print("Scraper health:")
        for sname, h in health.items():
            print("  " + sname.ljust(22) + "-> " + h.get("status", "?") +
                  "  (" + h.get("detail", "") + ")")

    listings = result.get("listings_results", {})
    if listings:
        print()
        print("Listings results:")
        for sname, r in listings.items():
            rung     = r.get("fallback_rung", "")
            rung_str = " [fallback:" + rung + "]" if rung else ""
            print("  " + sname.ljust(22) + "-> " + r.get("status", "?") +
                  rung_str + "  rows=" + str(r.get("rows", 0)))

    run_id = result.get("run_id", "?")
    print()
    print("Log file      : logs/pipeline.log")
    print("Run report    : logs/run_" + run_id + ".json")
    if qr.get("html_report"):
        print("Quality HTML  : " + qr["html_report"])
    print(sep)


# ── Path A: LangGraph (recommended) ──────────────────────────────────────────
if LANGGRAPH_AVAILABLE:

    # Standard automated run — QualityGuardAgent runs as node_quality_guard
    result = run_pipeline_graph(hitl_on_quality=False)

    # Production run — pause at quality_guard for human approval before finalising:
    # result = run_pipeline_graph(hitl_on_quality=True)

    # Resume a crashed or paused run by its run_id:
    # result = run_pipeline_graph(resume_thread_id="20250401_143022")

    # Override approval threshold for this run only:
    # result = run_pipeline_graph()  # after setting state["quality_threshold"] = 70

    _print_summary(result, mode="LangGraph")

# ── Path B: Legacy OrchestratorAgent (fallback if LangGraph not installed) ───
else:
    print("LangGraph not available — using OrchestratorAgent + QualityGuardAgent directly.")
    print("Install with: pip install langgraph\n")

    orchestrator = OrchestratorAgent()
    result       = orchestrator.run()

    # Phase 6: run QualityGuardAgent explicitly on the legacy path
    result = _quality_agent.run(result)

    _print_summary(result, mode="Legacy")
