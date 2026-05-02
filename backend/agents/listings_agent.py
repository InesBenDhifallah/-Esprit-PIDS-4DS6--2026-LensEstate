import glob
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from base import BaseAgent, FallbackMixin
from llm import call_llm, parse_llm_json
from config import (
    MUBAWAB_CWD, MUBAWAB_SCRIPT, MUBAWAB_OUTPUT_CSV,
    TAYARA_CWD, TAYARA_SCRIPT, TAYARA_OUTPUT_DIR, TAYARA_OUTPUT_GLOB,
    TUNISIE_CWD, TUNISIE_SCRIPT, TUNISIE_OUTPUT_CSV,
)


class ListingsAgent(BaseAgent, FallbackMixin):
    """
    Runs Mubawab, Tayara, and Tunisie Annonces scrapers.
    Phase 2: ReAct loop — LLM decides run/skip order.
    Phase 3: FallbackMixin — 4-rung degradation ladder.
    """

    SCRAPERS = {
        "mubawab": {
            "cwd"        : MUBAWAB_CWD,
            "script"     : MUBAWAB_SCRIPT,
            "args"       : [],
            "output_csv" : MUBAWAB_OUTPUT_CSV,
            "min_rows"   : 100,
            "timeout"    : 7200,
        },
        "tayara": {
            "cwd"        : TAYARA_CWD,
            "script"     : TAYARA_SCRIPT,
            "args"       : ["--max-pages", "13"],
            "output_dir" : TAYARA_OUTPUT_DIR,
            "output_glob": TAYARA_OUTPUT_GLOB,
            "min_rows"   : 100,
            "timeout"    : 3600,
        },
        "tunisie_annonce": {
            "cwd"        : TUNISIE_CWD,
            "script"     : TUNISIE_SCRIPT,
            "args"       : [],
            "output_csv" : TUNISIE_OUTPUT_CSV,
            "min_rows"   : 100,
            "timeout"    : 7200,
        },
    }
    MAX_OUTPUT_AGE_HOURS = 6
    MAX_RECENT_FAILURES  = 3
    MAX_RETRIES          = 3
    BASE_BACKOFF         = 10
    MAX_REACT_STEPS      = 14

    def __init__(self):
        super().__init__("ListingsAgent")

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log.info("=" * 60)
        self.log.info("ListingsAgent — starting (ReAct + Fallback)")
        self.log.info("=" * 60)
        self.memory.clear()

        health: Dict = state.get("scraper_health", {})
        if health:
            self.log.info(f"Health context: {state.get('scraper_health_summary','')}")
        else:
            self.log.info("No health data available — running without pre-flight context")

        collected, results = self._react_loop(health)

        real_collected  = [p for p in collected if self.SYNTHETIC_SOURCE_TAG not in p]
        synth_collected = [p for p in collected if self.SYNTHETIC_SOURCE_TAG in p]

        if real_collected:
            final_collected = real_collected
            if synth_collected:
                self.log.warning(f"Dropping {len(synth_collected)} synthetic file(s) — real data available")
        else:
            final_collected = synth_collected
            if synth_collected:
                self.log.warning("ALL real scrapers failed — passing synthetic placeholder data downstream.")

        total_rows = sum(self._count_rows(p) for p in final_collected)
        state = self.update_state(state, "listings_raw_paths",    final_collected)
        state = self.update_state(state, "listings_results",      results)
        state = self.update_state(state, "listings_total_rows",   total_rows)
        state = self.update_state(state, "listings_has_synthetic",
                                  len(synth_collected) > 0 and not real_collected)

        self.log.info(f"\nListingsAgent done — {len(final_collected)} sources, {total_rows:,} total rows")
        for name, r in results.items():
            rung     = r.get("fallback_rung", "")
            rung_str = f" [{rung}]" if rung else ""
            self.log.info(f"  {name:<22} → {r['status']}{rung_str}")
        return state

    def _react_loop(self, health: Dict) -> Tuple[List[str], Dict]:
        collected: List[str] = []
        results:   Dict      = {}
        handled:   set       = set()

        scraper_summary = {
            name: {
                **self._inspect_scraper(name, cfg),
                "site_health": health.get(name, {}).get("status", "unknown"),
                "site_detail": health.get(name, {}).get("detail", ""),
            }
            for name, cfg in self.SCRAPERS.items()
        }

        system_context = (
            "You are ListingsAgent for LensEstate, a Tunisian real estate platform.\n"
            "Manage three listing scrapers: mubawab, tayara, tunisie_annonce.\n\n"
            "Available tools (call ONE per step):\n"
            "  inspect_scraper(name)           — full state: age, rows, failures, site health\n"
            "  run_scraper(name)               — execute the scraper subprocess\n"
            "  skip_scraper(name, reason)      — skip and use best available cache\n"
            "  activate_fallback(name, reason) — site blocked/down: trigger degradation ladder\n"
            "  finish()                        — all scrapers handled\n\n"
            "Decision rules:\n"
            "  SKIP if output fresh (< 6h) AND rows >= min_rows\n"
            "  SKIP if recent_failures >= 3 AND no valid output\n"
            "  RUN  if output stale/missing AND site_health is 'healthy'\n"
            "  ACTIVATE_FALLBACK if site_health is 'blocked' or 'down'\n\n"
            f"Current states:\n{json.dumps(scraper_summary, indent=2)}\n\n"
            'Reply ONLY with JSON: {"thought": "reasoning", "tool": "tool_name", "args": {"key": "value"}}'
        )

        messages = [{"role": "user", "content": system_context}]

        for step in range(self.MAX_REACT_STEPS):
            self.log.info(f"\n  [ReAct step {step+1}/{self.MAX_REACT_STEPS}]")

            recent = messages[-4:] if len(messages) > 4 else messages
            prompt = "\n---\n".join(m["content"] for m in recent)

            raw    = call_llm(prompt, max_tokens=512)
            parsed = parse_llm_json(raw)

            thought = parsed.get("thought", "")
            tool    = parsed.get("tool", "finish")
            args    = parsed.get("args", {})

            self.log.info(f"  thought : {thought[:220]}")
            self.log.info(f"  tool    : {tool}  args={args}")

            if tool == "inspect_scraper":
                name        = args.get("name", "")
                result_data = {
                    **self._inspect_scraper(name, self.SCRAPERS.get(name, {})),
                    "site_health": health.get(name, {}).get("status", "unknown"),
                }
                tool_result = json.dumps(result_data)
                self.log.info(f"  → {tool_result[:280]}")

            elif tool == "run_scraper":
                name = args.get("name", "")
                cfg  = self.SCRAPERS.get(name)
                if not cfg:
                    tool_result = f"Unknown scraper: {name}"
                else:
                    success, path = self._run_with_retry(name, cfg)
                    if success and path:
                        rows = self._count_rows(path)
                        collected.append(path)
                        results[name] = {"status": "success", "path": path, "rows": rows}
                        self.memory.remember("successes", {"scraper": name, "rows": rows})
                        tool_result = f"Success — {rows:,} rows"
                        self.log.info(f"  ✅ {name} → {rows:,} rows")
                    else:
                        self.log.warning(f"  {name} failed — activating fallback ladder")
                        h_status = health.get(name, {}).get("status", "unknown")
                        rung, fpath, explanation = self.resolve_fallback(
                            name, cfg, h_status,
                            find_output_fn=self._find_output,
                            count_rows_fn=self._count_rows,
                        )
                        if fpath:
                            collected.append(fpath)
                            rows = self._count_rows(fpath)
                            results[name] = {
                                "status":        "fallback",
                                "fallback_rung": rung,
                                "path":          fpath,
                                "rows":          rows,
                                "explanation":   explanation,
                            }
                            self.memory.remember("failures", {"scraper": name, "reason": "run_failed_fallback_activated", "rung": rung})
                            tool_result = f"Failed → fallback {rung}: {explanation}"
                            self.log.warning(f"  ⚠️  {name} → {tool_result}")
                        else:
                            results[name] = {"status": "failed"}
                            self.memory.remember("failures", {"scraper": name, "reason": "retries_exhausted_no_fallback"})
                            tool_result = "Failed — all retries exhausted, no fallback available"
                            self.log.error(f"  ❌ {name} → {tool_result}")
                    handled.add(name)

            elif tool == "activate_fallback":
                name   = args.get("name", "")
                cfg    = self.SCRAPERS.get(name, {})
                h_status = health.get(name, {}).get("status", "unknown")
                rung, fpath, explanation = self.resolve_fallback(
                    name, cfg, h_status,
                    find_output_fn=self._find_output,
                    count_rows_fn=self._count_rows,
                )
                if fpath:
                    collected.append(fpath)
                    rows = self._count_rows(fpath)
                    results[name] = {"status": "fallback", "fallback_rung": rung, "path": fpath, "rows": rows, "explanation": explanation}
                    tool_result = f"Fallback {rung}: {explanation}"
                else:
                    results[name] = {"status": "failed"}
                    tool_result = "No fallback available"
                handled.add(name)
                self.log.info(f"  ⚠️  {name} → {tool_result}")

            elif tool == "skip_scraper":
                name   = args.get("name", "")
                reason = args.get("reason", "")
                cfg    = self.SCRAPERS.get(name, {})
                existing = self._find_output(cfg)
                if existing:
                    collected.append(existing)
                    rows = self._count_rows(existing)
                    results[name] = {"status": "skipped", "reason": reason, "path": existing, "rows": rows}
                    tool_result = f"Skipped — using cache: {rows} rows"
                else:
                    results[name] = {"status": "skipped", "reason": reason}
                    tool_result = "Skipped — no cache"
                handled.add(name)
                self.log.info(f"  ⏭  {name}: {tool_result}")

            elif tool == "finish":
                self.log.info("  LLM called finish() — exiting loop")
                break

            else:
                tool_result = f"Unknown tool '{tool}'"
                self.log.warning(f"  ⚠  {tool_result}")

            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user",      "content": f"Tool result: {tool_result}"})

            if handled >= set(self.SCRAPERS.keys()):
                self.log.info("  All scrapers handled — exiting loop")
                break

        # safety net
        for name, cfg in self.SCRAPERS.items():
            if name not in handled and name not in results:
                self.log.warning(f"  Safety net: {name}")
                existing = self._find_output(cfg)
                if existing:
                    rows = self._count_rows(existing)
                    collected.append(existing)
                    results[name] = {"status": "skipped", "reason": "safety_net", "rows": rows}
                else:
                    success, path = self._run_with_retry(name, cfg)
                    if success and path:
                        rows = self._count_rows(path)
                        collected.append(path)
                        results[name] = {"status": "success", "path": path, "rows": rows}
                    else:
                        results[name] = {"status": "failed"}

        return collected, results

    def _find_output(self, cfg: Dict) -> Optional[str]:
        if "output_csv" in cfg and Path(cfg["output_csv"]).exists():
            return cfg["output_csv"]
        if "output_dir" in cfg and "output_glob" in cfg:
            files = sorted(
                glob.glob(str(Path(cfg["output_dir"]) / cfg["output_glob"])),
                key=lambda p: Path(p).stat().st_mtime,
                reverse=True,
            )
            if files:
                return files[0]
        return None

    def _inspect_scraper(self, name: str, cfg: Dict) -> Dict:
        import os
        existing = self._find_output(cfg)
        output_info = {"exists": False, "rows": 0, "age_hours": None, "fresh": False}
        if existing:
            age_h = (time.time() - os.path.getmtime(existing)) / 3600
            rows  = self._count_rows(existing)
            output_info = {
                "exists":    True,
                "rows":      rows,
                "age_hours": round(age_h, 1),
                "fresh":     age_h < self.MAX_OUTPUT_AGE_HOURS and rows >= cfg.get("min_rows", 100),
            }
        recent_failures = [f for f in self.memory.recall("failures", 20) if f.get("scraper") == name]
        return {
            "scraper":         name,
            "min_rows":        cfg.get("min_rows", 100),
            "output":          output_info,
            "recent_failures": len(recent_failures),
            "last_failure":    recent_failures[-1] if recent_failures else None,
            "manual_override": self._find_manual(name) is not None,
        }

    def _run_with_retry(self, name: str, cfg: Dict) -> Tuple[bool, Optional[str]]:
        backoff = self.BASE_BACKOFF
        python  = self._resolve_python(cfg["cwd"])
        cmd = [python, cfg["script"]] + cfg.get("args", [])
        for attempt in range(1, self.MAX_RETRIES + 1):
            self.log.info(f"  Attempt {attempt}/{self.MAX_RETRIES}")
            success, _, _ = self._run_subprocess(cmd, cfg["cwd"], cfg.get("timeout", 3600))
            if success:
                path = self._find_output(cfg)
                if path:
                    rows = self._count_rows(path)
                    if rows >= cfg.get("min_rows", 100):
                        return True, path
                    self.log.warning(f"  Too few rows: {rows} < {cfg.get('min_rows', 100)}")
                else:
                    self.log.warning(f"  Output not found after scrape")
            if attempt < self.MAX_RETRIES:
                self.log.info(f"  Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
        return False, None
