# ─────────────────────────────────────────────────────────────────────────────
# CELL 119d — Phase 6: QualityGuardAgent
# INSERT after Cell 121 (Phase 5 / LangGraph), before Cell 122 (run cell)
#
# Adds:
#   QualityGuardAgent  — standalone agent with deep quality analysis, LLM
#                        narrative, configurable approval threshold, and an
#                        HTML quality report saved to logs/quality_{run_id}.html
#
# The Phase 5 node_quality_guard is replaced by a thin wrapper that delegates
# to QualityGuardAgent.run() — so both the LangGraph path and the legacy
# OrchestratorAgent path share the same quality logic.
# ─────────────────────────────────────────────────────────────────────────────


class QualityGuardAgent(BaseAgent):
    """
    Dedicated quality scoring agent — the final gate before a pipeline run
    is marked successful.

    Responsibilities:
      1. Compute a structured 0–100 quality score across 5 dimensions.
      2. Ask the LLM for a narrative assessment and an approval decision.
      3. Persist the full quality report as:
           - state["quality_report"]  (dict, available downstream)
           - logs/quality_{run_id}.html  (human-readable HTML report)
           - memory "quality" category  (for weekly review / heuristics)

    Score dimensions (each 0–20, total 0–100):
      D1  Row volume      — how close to MIN_LISTINGS
      D2  Data freshness  — real data vs fallback/synthetic
      D3  Completeness    — null rates on critical columns
      D4  Consistency     — suspicious row rate from CleaningAgent
      D5  Source balance  — no single source dominates > 90%

    Approval threshold: score >= APPROVE_THRESHOLD (default 60).
    Can be overridden per-run via state["quality_threshold"].
    """

    APPROVE_THRESHOLD = 60     # score below this triggers a warning / HITL pause
    MIN_LISTINGS      = 500    # mirrors OrchestratorAgent.MIN_LISTINGS

    # Dimension weights (must sum to 100)
    WEIGHTS = {
        "row_volume":    25,
        "data_freshness": 20,
        "completeness":  25,
        "consistency":   15,
        "source_balance": 15,
    }

    def __init__(self):
        super().__init__("QualityGuardAgent")

    # ── Public entry point ─────────────────────────────────────────────────────
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log.info("=" * 60)
        self.log.info("QualityGuardAgent — quality assessment")
        self.log.info("=" * 60)
        self.memory.clear()

        run_id    = state.get("run_id", "unknown")
        threshold = state.get("quality_threshold", self.APPROVE_THRESHOLD)

        # ── 1. Compute structured score ───────────────────────────────────
        scores, details = self._compute_scores(state)
        total = round(sum(scores.values()), 1)

        self.log.info(f"\nQuality scores:")
        for dim, s in scores.items():
            max_s = self.WEIGHTS[dim]
            bar   = "█" * int(s / max_s * 10) + "░" * (10 - int(s / max_s * 10))
            self.log.info(f"  {dim:<18} [{bar}] {s:.1f}/{max_s}")
        self.log.info(f"  {'TOTAL':<18}  {total:.1f}/100")

        # ── 2. LLM narrative + approval ───────────────────────────────────
        narrative, approved, llm_thought = self._llm_assess(
            state, scores, total, threshold
        )
        self.log.info(f"\nLLM thought   : {llm_thought[:200]}")
        self.log.info(f"LLM narrative : {narrative[:200]}")
        self.log.info(f"Approved      : {approved}  (threshold={threshold})")

        # ── 3. Determine pipeline status ──────────────────────────────────
        has_synth = state.get("listings_has_synthetic", False)
        final_rows = state.get("final_row_count", 0)

        if approved and not has_synth:
            pipeline_status = "success"
        elif approved and has_synth:
            pipeline_status = "degraded_synthetic"
        elif final_rows > 0:
            pipeline_status = "degraded"
        else:
            pipeline_status = "failed"

        # ── 4. Assemble full quality report dict ──────────────────────────
        quality_report = {
            "run_id":             run_id,
            "total_score":        total,
            "threshold":          threshold,
            "approved":           approved,
            "pipeline_status":    pipeline_status,
            "dimension_scores":   scores,
            "dimension_details":  details,
            "narrative":          narrative,
            "llm_thought":        llm_thought,
            "final_row_count":    final_rows,
            "has_synthetic":      has_synth,
            "assessed_at":        _now(),
        }

        # ── 5. Save HTML report ───────────────────────────────────────────
        html_path = self._save_html_report(quality_report)
        quality_report["html_report"] = html_path
        self.log.info(f"\nHTML report   : {html_path}")

        # ── 6. Persist to memory ──────────────────────────────────────────
        self.memory.remember("quality", {
            "run_id": run_id,
            "score":  total,
            "approved": approved,
            "status": pipeline_status,
        })

        # ── 7. Update state ───────────────────────────────────────────────
        state = self.update_state(state, "quality_report",    quality_report)
        state = self.update_state(state, "quality_score",     total)
        state = self.update_state(state, "quality_approved",  approved)
        state = self.update_state(state, "quality_notes",     narrative)
        state = self.update_state(state, "pipeline_status",   pipeline_status)

        self.log.info(f"\n{'─'*60}")
        self.log.info(f"QualityGuardAgent done — {pipeline_status.upper()}  score={total}/100")
        self.log.info(f"{'─'*60}")
        return state

    # ── Score computation ──────────────────────────────────────────────────────
    def _compute_scores(
        self, state: Dict
    ) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """
        Returns (scores dict, details dict).
        Each score is 0–weight[dim], summing to 0–100.
        """
        cleaning_report  = state.get("cleaning_report", {})
        listings_results = state.get("listings_results", {})
        final_rows       = state.get("final_row_count", 0)
        has_synth        = state.get("listings_has_synthetic", False)
        null_rate        = cleaning_report.get("null_rate", {})
        suspicious       = cleaning_report.get("suspicious", 0)

        scores  = {}
        details = {}

        # ── D1: Row volume (0-25) ─────────────────────────────────────────
        w = self.WEIGHTS["row_volume"]
        if final_rows >= self.MIN_LISTINGS:
            d1 = w
        elif final_rows > 0:
            d1 = round(w * (final_rows / self.MIN_LISTINGS) ** 0.7, 2)
        else:
            d1 = 0.0
        scores["row_volume"]  = d1
        details["row_volume"] = {
            "final_rows":    final_rows,
            "target":        self.MIN_LISTINGS,
            "score":         d1,
            "max":           w,
        }

        # ── D2: Data freshness (0-20) ─────────────────────────────────────
        w  = self.WEIGHTS["data_freshness"]
        n_success  = sum(1 for r in listings_results.values() if r.get("status") == "success")
        n_fallback = sum(1 for r in listings_results.values() if r.get("status") == "fallback")
        n_total    = max(len(listings_results), 1)

        freshness_ratio = n_success / n_total
        d2 = round(w * freshness_ratio, 2)
        if has_synth:
            d2 = round(d2 * 0.5, 2)   # heavy penalty for synthetic data

        # Check fallback rungs — cache_soft is better than cache_stale
        rungs = [r.get("fallback_rung", "") for r in listings_results.values()
                 if r.get("status") == "fallback"]
        rung_penalty = sum({"cache_stale": 3, "synthetic": 8}.get(rg, 0) for rg in rungs)
        d2 = max(0.0, round(d2 - rung_penalty, 2))

        scores["data_freshness"]  = d2
        details["data_freshness"] = {
            "sources_succeeded": n_success,
            "sources_fallback":  n_fallback,
            "has_synthetic":     has_synth,
            "fallback_rungs":    rungs,
            "score":             d2,
            "max":               w,
        }

        # ── D3: Completeness (0-25) ───────────────────────────────────────
        w = self.WEIGHTS["completeness"]
        critical_cols = {
            "price":        0.40,   # penalty threshold
            "surface_m2":   0.45,
            "governorate":  0.20,
            "property_type": 0.25,
        }
        col_scores = []
        col_details = {}
        for col, threshold in critical_cols.items():
            rate = null_rate.get(col, 0.0)
            if rate <= threshold:
                col_s = 1.0
            else:
                col_s = max(0.0, 1.0 - (rate - threshold) / (1.0 - threshold))
            col_scores.append(col_s)
            col_details[col] = {"null_rate": round(rate, 3), "score_ratio": round(col_s, 3)}

        d3 = round(w * (sum(col_scores) / len(col_scores)), 2) if col_scores else w
        scores["completeness"]  = d3
        details["completeness"] = {"columns": col_details, "score": d3, "max": w}

        # ── D4: Consistency (0-15) ────────────────────────────────────────
        w = self.WEIGHTS["consistency"]
        susp_rate = suspicious / max(final_rows, 1)
        if susp_rate <= 0.02:
            d4 = w
        elif susp_rate <= 0.10:
            d4 = round(w * (1 - (susp_rate - 0.02) / 0.08), 2)
        else:
            d4 = 0.0
        scores["consistency"]  = d4
        details["consistency"] = {
            "suspicious_rows":  suspicious,
            "suspicious_rate":  round(susp_rate, 4),
            "score":            d4,
            "max":              w,
        }

        # ── D5: Source balance (0-15) ─────────────────────────────────────
        w = self.WEIGHTS["source_balance"]
        row_counts = [r.get("rows", 0) for r in listings_results.values()
                      if r.get("rows", 0) > 0]
        if len(row_counts) >= 2:
            total_r   = sum(row_counts)
            max_share = max(row_counts) / total_r if total_r > 0 else 1.0
            # Penalty only if one source > 90% of all rows
            d5 = round(w * max(0.0, 1.0 - max(0.0, max_share - 0.9) / 0.1), 2)
        elif len(row_counts) == 1:
            d5 = round(w * 0.6, 2)   # single source — partial credit
        else:
            d5 = 0.0
        scores["source_balance"]  = d5
        details["source_balance"] = {
            "source_row_counts": row_counts,
            "score":             d5,
            "max":               w,
        }

        return scores, details

    # ── LLM assessment ─────────────────────────────────────────────────────────
    def _llm_assess(
        self,
        state:     Dict,
        scores:    Dict[str, float],
        total:     float,
        threshold: int,
    ) -> Tuple[str, bool, str]:
        """Ask the LLM for a narrative + approval decision."""

        cleaning_report = state.get("cleaning_report", {})
        listings_results = state.get("listings_results", {})

        source_summary = {
            name: {
                "status":        r.get("status"),
                "rows":          r.get("rows", 0),
                "fallback_rung": r.get("fallback_rung", ""),
            }
            for name, r in listings_results.items()
        }

        prompt = (
            f"You are the QualityGuardAgent for LensEstate, run {state.get('run_id')}.\n\n"
            f"Quality score: {total}/100  (approval threshold: {threshold}/100)\n\n"
            f"Dimension scores:\n"
            + "\n".join(
                f"  {dim:<18}: {s:.1f}/{self.WEIGHTS[dim]}"
                for dim, s in scores.items()
            )
            + f"\n\nData context:\n"
            f"  Final rows     : {state.get('final_row_count', 0):,}\n"
            f"  Has synthetic  : {state.get('listings_has_synthetic', False)}\n"
            f"  Null rates     : {cleaning_report.get('null_rate', {})}\n"
            f"  Suspicious rows: {cleaning_report.get('suspicious', 0)}\n"
            f"  Sources        : {json.dumps(source_summary)}\n\n"
            f"Write a 3-sentence quality assessment covering:\n"
            f"  1. What the data quality looks like overall\n"
            f"  2. The biggest weakness in this run\n"
            f"  3. Whether this dataset is fit for model training\n\n"
            f"Approve if total >= {threshold} AND at least some real (non-synthetic) data exists.\n\n"
            f'Return ONLY JSON:\n'
            f'{{"thought": "...", "approved": true/false, "narrative": "3-sentence assessment"}}'
        )

        result    = self.decide(prompt, model=LLM_FALLBACK)
        thought   = result.get("thought", "")
        narrative = result.get("narrative", f"Quality score {total}/100.")
        approved  = result.get("approved", total >= threshold)

        return narrative, bool(approved), thought

    # ── HTML report ────────────────────────────────────────────────────────────
    def _save_html_report(self, report: Dict) -> str:
        """Generate and save a human-readable HTML quality report."""

        run_id  = report.get("run_id", "unknown")
        total   = report.get("total_score", 0)
        status  = report.get("pipeline_status", "?").upper()
        scores  = report.get("dimension_scores", {})
        details = report.get("dimension_details", {})

        status_color = {
            "SUCCESS":             "#1D9E75",
            "DEGRADED_SYNTHETIC":  "#BA7517",
            "DEGRADED":            "#BA7517",
            "FAILED":              "#A32D2D",
        }.get(status, "#888780")

        score_color = "#1D9E75" if total >= 80 else "#BA7517" if total >= 60 else "#A32D2D"

        def dim_row(dim, score):
            w    = self.WEIGHTS.get(dim, 20)
            pct  = int(score / w * 100)
            bar_color = "#1D9E75" if pct >= 80 else "#BA7517" if pct >= 50 else "#A32D2D"
            label = dim.replace("_", " ").title()
            return (
                f"<tr><td style='padding:8px 12px;font-size:13px'>{label}</td>"
                f"<td style='padding:8px 12px'>"
                f"<div style='background:#f0f0f0;border-radius:4px;height:16px;width:200px'>"
                f"<div style='background:{bar_color};width:{pct}%;height:16px;border-radius:4px'></div>"
                f"</div></td>"
                f"<td style='padding:8px 12px;font-size:13px;font-weight:500'>{score:.1f}/{w}</td>"
                f"<td style='padding:8px 12px;font-size:12px;color:#666'>{self._detail_str(dim, details.get(dim, {}))}</td>"
                f"</tr>"
            )

        rows_html = "\n".join(dim_row(d, s) for d, s in scores.items())

        narrative = report.get("narrative", "").replace("\n", "<br>")
        sources   = report.get("dimension_details", {}).get("data_freshness", {})
        null_info = report.get("dimension_details", {}).get("completeness", {}).get("columns", {})
        null_rows = "\n".join(
            f"<tr><td style='padding:4px 12px;font-size:12px'>{col}</td>"
            f"<td style='padding:4px 12px;font-size:12px'>{info.get('null_rate',0)*100:.1f}%</td></tr>"
            for col, info in null_info.items()
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>LensEstate Quality Report — {run_id}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          max-width: 900px; margin: 40px auto; padding: 0 24px; color: #1a1a1a; }}
  h1   {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
  h2   {{ font-size: 16px; font-weight: 500; margin: 28px 0 12px; color: #333; }}
  .meta {{ font-size: 13px; color: #666; margin-bottom: 28px; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px;
             font-size: 13px; font-weight: 500; color: #fff;
             background: {status_color}; margin-left: 10px; vertical-align: middle; }}
  .score-big {{ font-size: 52px; font-weight: 700; color: {score_color};
                 line-height: 1; display: inline-block; }}
  .score-label {{ font-size: 14px; color: #666; vertical-align: bottom;
                   padding-bottom: 8px; margin-left: 6px; }}
  .card {{ background: #f8f8f8; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  th {{ text-align: left; padding: 8px 12px; font-size: 12px;
        font-weight: 500; color: #888; border-bottom: 1px solid #e8e8e8; }}
  .narrative {{ font-size: 14px; line-height: 1.7; color: #333; }}
  .footer {{ font-size: 12px; color: #aaa; margin-top: 40px; border-top: 1px solid #eee;
              padding-top: 16px; }}
</style>
</head>
<body>
<h1>LensEstate Pipeline Quality Report <span class="badge">{status}</span></h1>
<p class="meta">Run ID: <strong>{run_id}</strong> &nbsp;·&nbsp; Assessed: {report.get("assessed_at","")[:19]}</p>

<div class="card" style="display:flex;align-items:flex-end;gap:32px">
  <div>
    <div class="score-big">{total}</div>
    <span class="score-label">/100 &nbsp; (threshold: {report.get("threshold",60)})</span>
  </div>
  <div style="font-size:13px;color:#555;max-width:400px">
    <strong>Final rows:</strong> {report.get("final_row_count",0):,} &nbsp;
    <strong>Synthetic:</strong> {"yes" if report.get("has_synthetic") else "no"}<br>
    <strong>Approved:</strong> {"✅ yes" if report.get("approved") else "❌ no"}
  </div>
</div>

<h2>Quality dimensions</h2>
<table>
  <tr><th>Dimension</th><th>Score</th><th>Points</th><th>Detail</th></tr>
  {rows_html}
</table>

<h2>LLM assessment</h2>
<div class="card narrative">{narrative}</div>

<h2>Null rates (critical columns)</h2>
<table>
  <tr><th>Column</th><th>Null rate</th></tr>
  {null_rows}
</table>

<div class="footer">
  Generated by QualityGuardAgent · LensEstate pipeline · {report.get("assessed_at","")[:10]}
</div>
</body>
</html>"""

        out_dir = Path("logs")
        out_dir.mkdir(exist_ok=True)
        out_path = str(out_dir / f"quality_{run_id}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        return out_path

    def _detail_str(self, dim: str, detail: Dict) -> str:
        """One-line detail string per dimension for the HTML table."""
        if dim == "row_volume":
            return f"{detail.get('final_rows',0):,} rows / {detail.get('target',0):,} target"
        if dim == "data_freshness":
            return (
                f"{detail.get('sources_succeeded',0)} fresh, "
                f"{detail.get('sources_fallback',0)} fallback"
                + (" + synthetic" if detail.get("has_synthetic") else "")
            )
        if dim == "completeness":
            worst = max(detail.get("columns", {}).items(),
                        key=lambda x: x[1].get("null_rate", 0),
                        default=("?", {"null_rate": 0}))
            return f"worst: {worst[0]} {worst[1].get('null_rate',0)*100:.1f}% null"
        if dim == "consistency":
            return f"{detail.get('suspicious_rows',0)} suspicious ({detail.get('suspicious_rate',0)*100:.1f}%)"
        if dim == "source_balance":
            counts = detail.get("source_row_counts", [])
            return f"{len(counts)} active sources"
        return ""


# ── Global singleton ──────────────────────────────────────────────────────────
_quality_agent = QualityGuardAgent()

# ── Patch node_quality_guard to delegate to QualityGuardAgent ────────────────
# This replaces the inline scoring logic in the Phase 5 LangGraph cell
# so both the LangGraph path and the legacy path share the same code.

if LANGGRAPH_AVAILABLE:
    def node_quality_guard(state: PipelineState) -> PipelineState:
        """
        Phase 6 upgrade: delegates entirely to QualityGuardAgent.
        Same signature as before — LangGraph graph definition unchanged.
        """
        _log = _build_logger("Graph.quality_guard")
        _log.info("█" * 60)
        _log.info("  NODE: quality_guard  (QualityGuardAgent)")

        # Apply HITL threshold from state if set, else use default
        result = _quality_agent.run(dict(state))
        return result


print("✅ QualityGuardAgent defined (Phase 6)")
print()
print("Outputs per run:")
print("  state['quality_report']           — full structured dict")
print("  state['quality_score']            — float 0-100")
print("  state['quality_approved']         — bool")
print("  logs/quality_{run_id}.html        — human-readable HTML report")
print("  memory 'quality' category         — persisted for weekly review")
print()
print("To set a custom approval threshold for one run:")
print("  state['quality_threshold'] = 70   # before calling run_pipeline_graph()")
