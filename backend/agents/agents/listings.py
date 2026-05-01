# ─────────────────────────────────────────────────────────────────────────────
# CELL 115 — ListingsAgent  (Phase 2 + Phase 3 combined — full replacement)
# ─────────────────────────────────────────────────────────────────────────────

class ListingsAgent(BaseAgent, FallbackMixin):
    """
    Runs Mubawab, Tayara, and Tunisie Annonces scrapers.

    Phase 2: ReAct loop — LLM decides run/skip order with reasoning.
    Phase 3: FallbackMixin — 4-rung degradation ladder when scraper fails.
             ScraperHealthAgent results inform the LLM and fallback choices.
    """

    SCRAPERS = {
        "mubawab": {
            "cwd"        : r"C:\Mubawab-scrapper",
            "script"     : "mubawab_scraper.py",
            "args"       : [],
            "output_csv" : r"C:\Mubawab-scrapper\data\mubawab_listings.csv",
            "min_rows"   : 100,
            "timeout"    : 7200,
        },
        "tayara": {
            "cwd"        : r"C:\tayara-scraper",
            "script"     : "main.py",
            "args"       : ["--max-pages", "13"],
            "output_dir" : r"C:\tayara-scraper\data\tayara_scrape\processed",
            "output_glob": "tayara_listings_*.csv",
            "min_rows"   : 100,
            "timeout"    : 3600,
        },
        "tunisie_annonce": {
            "cwd"        : r"C:\Tunisie-Annonces-scrapper",
            "script"     : "main.py",
            "args"       : [],
            "output_csv" : r"C:\Tunisie-Annonces-scrapper\output\tunisie_annonce_listings.csv",
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

    # ── Public entry point ────────────────────────────────────────────────────
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log.info("=" * 60)
        self.log.info("ListingsAgent — starting (ReAct + Fallback)")
        self.log.info("=" * 60)
        self.memory.clear()

        # Pull health results from ScraperHealthAgent (may be absent if skipped)
        health: Dict = state.get("scraper_health", {})
        if health:
            self.log.info(f"Health context: {state.get('scraper_health_summary','')}")
        else:
            self.log.info("No health data available — running without pre-flight context")

        collected, results = self._react_loop(health)

        # Strip synthetic rows from collected paths — they must not reach
        # StandardizationAgent unless every real source failed
        real_collected   = [p for p in collected if self.SYNTHETIC_SOURCE_TAG not in p]
        synth_collected  = [p for p in collected if self.SYNTHETIC_SOURCE_TAG in p]

        if real_collected:
            final_collected = real_collected
            if synth_collected:
                self.log.warning(
                    f"Dropping {len(synth_collected)} synthetic file(s) — real data available"
                )
        else:
            # All real scrapers failed — pass synthetic through so pipeline can continue
            final_collected = synth_collected
            if synth_collected:
                self.log.warning(
                    "ALL real scrapers failed — passing synthetic placeholder data downstream. "
                    "Final model CSV will exclude synthetic rows."
                )

        total_rows = sum(self._count_rows(p) for p in final_collected)
        state = self.update_state(state, "listings_raw_paths",   final_collected)
        state = self.update_state(state, "listings_results",     results)
        state = self.update_state(state, "listings_total_rows",  total_rows)
        state = self.update_state(state, "listings_has_synthetic",
                                  len(synth_collected) > 0 and not real_collected)

        self.log.info(f"\nListingsAgent done — {len(final_collected)} sources, {total_rows:,} total rows")
        for name, r in results.items():
            rung = r.get("fallback_rung", "")
            rung_str = f" [{rung}]" if rung else ""
            self.log.info(f"  {name:<22} → {r['status']}{rung_str}")
        return state

    # ── ReAct loop ────────────────────────────────────────────────────────────
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
            "  ACTIVATE_FALLBACK if site_health is 'blocked' or 'down'\n"
            "  Think about order — start with the most reliable scraper\n\n"
            f"Current states:\n{json.dumps(scraper_summary, indent=2)}\n\n"
            'Reply ONLY with JSON: {"thought": "reasoning with specific numbers", '
            '"tool": "tool_name", "args": {"key": "value"}}'
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

            # ── Tool dispatch ─────────────────────────────────────────────
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
                        # Scraper failed — immediately try fallback
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
                            self.memory.remember("failures", {
                                "scraper": name, "reason": "run_failed_fallback_activated",
                                "rung": rung,
                            })
                            tool_result = f"Failed → fallback {rung}: {explanation}"
                            self.log.warning(f"  ⚠️  {name} → {tool_result}")
                        else:
                            results[name] = {"status": "failed"}
                            self.memory.remember("failures", {
                                "scraper": name, "reason": "retries_exhausted_no_fallback",
                            })
                            tool_result = f"Failed — all retries exhausted, no fallback available"
                            self.log.error(f"  ❌ {name} → {tool_result}")
                    handled.add(name)

            elif tool == "activate_fallback":
                name   = args.get("name", "")
                reason = args.get("reason", "LLM requested fallback")
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
                    results[name] = {
                        "status":        "fallback",
                        "fallback_rung": rung,
                        "path":          fpath,
                        "rows":          rows,
                        "explanation":   explanation,
                        "llm_reason":    reason,
                    }
                    tool_result = f"Fallback {rung} activated: {explanation}"
                    self.log.warning(f"  ⚠️  {name} → {tool_result}")
                else:
                    results[name] = {"status": "failed", "reason": "no_fallback_available"}
                    tool_result = "No fallback available — source will be missing"
                    self.log.error(f"  ❌ {name} → {tool_result}")
                handled.add(name)

            elif tool == "skip_scraper":
                name   = args.get("name", "")
                reason = args.get("reason", "no reason given")
                cfg    = self.SCRAPERS.get(name, {})
                existing = self._find_output(cfg)
                if existing:
                    collected.append(existing)
                    rows = self._count_rows(existing)
                    results[name] = {"status": "skipped", "reason": reason,
                                     "path": existing, "rows": rows}
                    tool_result = f"Skipped — using cache: {rows:,} rows"
                else:
                    results[name] = {"status": "skipped", "reason": reason}
                    tool_result = f"Skipped — no cache"
                handled.add(name)
                self.log.info(f"  ⏭  {name}: {tool_result}")

            elif tool == "finish":
                self.log.info("  LLM called finish() — exiting ReAct loop")
                break

            else:
                tool_result = f"Unknown tool '{tool}'"
                self.log.warning(f"  ⚠  {tool_result}")

            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user",      "content": f"Tool result: {tool_result}"})

            if handled >= set(self.SCRAPERS.keys()):
                self.log.info("  All scrapers handled — exiting ReAct loop")
                break

        # Safety net
        for name, cfg in self.SCRAPERS.items():
            if name not in handled and name not in results:
                self.log.warning(f"  Safety net: handling missed scraper {name}")
                h_status = health.get(name, {}).get("status", "unknown")
                skip, reason = self._should_skip_fallback(name, cfg)
                if skip:
                    existing = self._find_output(cfg)
                    if existing:
                        collected.append(existing)
                    results[name] = {"status": "skipped", "reason": reason}
                else:
                    success, path = self._run_with_retry(name, cfg)
                    if success and path:
                        rows = self._count_rows(path)
                        collected.append(path)
                        results[name] = {"status": "success", "path": path, "rows": rows}
                        self.memory.remember("successes", {"scraper": name, "rows": rows})
                    else:
                        rung, fpath, explanation = self.resolve_fallback(
                            name, cfg, h_status,
                            find_output_fn=self._find_output,
                            count_rows_fn=self._count_rows,
                        )
                        if fpath:
                            collected.append(fpath)
                            results[name] = {"status": "fallback", "fallback_rung": rung,
                                             "path": fpath, "explanation": explanation}
                        else:
                            results[name] = {"status": "failed"}
                        self.memory.remember("failures", {"scraper": name, "reason": "safety_net"})

        return collected, results

    # ── Tool implementations (same as Phase 2) ────────────────────────────────
    def _inspect_scraper(self, name: str, cfg: Dict) -> Dict:
        existing = self._find_output(cfg)
        min_rows = cfg.get("min_rows", 100)

        output_info = {"exists": False, "rows": 0, "age_hours": None, "fresh": False}
        if existing and Path(existing).exists():
            age_h = (time.time() - os.path.getmtime(existing)) / 3600
            rows  = self._count_rows(existing)
            output_info = {
                "exists":    True,
                "path":      existing,
                "rows":      rows,
                "age_hours": round(age_h, 1),
                "fresh":     age_h < self.MAX_OUTPUT_AGE_HOURS and rows >= min_rows,
            }

        recent_failures  = [f for f in self.memory.recall("failures",  20) if f.get("scraper") == name]
        recent_successes = [s for s in self.memory.recall("successes", 20) if s.get("scraper") == name]

        # Check manual override
        manual = self._find_manual(name)

        return {
            "scraper":          name,
            "min_rows":         min_rows,
            "max_age_hours":    self.MAX_OUTPUT_AGE_HOURS,
            "output":           output_info,
            "recent_failures":  len(recent_failures),
            "recent_successes": len(recent_successes),
            "last_failure":     recent_failures[-1]  if recent_failures  else None,
            "last_success":     recent_successes[-1] if recent_successes else None,
            "manual_override":  manual is not None,
        }

    def _should_skip_fallback(self, name: str, cfg: Dict) -> Tuple[bool, str]:
        existing = self._find_output(cfg)
        if existing and Path(existing).exists():
            age_h = (time.time() - os.path.getmtime(existing)) / 3600
            rows  = self._count_rows(existing)
            if age_h < self.MAX_OUTPUT_AGE_HOURS and rows >= cfg["min_rows"]:
                return True, f"Fresh output ({age_h:.1f}h, {rows:,} rows)"
        recent_fail = [f for f in self.memory.recall("failures", 20) if f.get("scraper") == name]
        if len(recent_fail) >= self.MAX_RECENT_FAILURES:
            return True, f"Failed {len(recent_fail)}x recently"
        return False, "Output missing or stale"

    def _run_with_retry(self, name: str, cfg: Dict) -> Tuple[bool, Optional[str]]:
        backoff = self.BASE_BACKOFF
        python  = self._resolve_python(cfg["cwd"])
        self.log.info(f"  python : {python}")
        cmd = [python, cfg["script"]] + cfg.get("args", [])
        for attempt in range(1, self.MAX_RETRIES + 1):
            self.log.info(f"  Attempt {attempt}/{self.MAX_RETRIES}")
            ok, _, _ = self._run_subprocess(cmd, cfg["cwd"], cfg.get("timeout", 3600))
            if ok:
                path = self._find_output(cfg)
                if path:
                    rows = self._count_rows(path)
                    if rows >= cfg["min_rows"]:
                        return True, path
                    self.log.warning(f"  Too few rows: {rows} < {cfg['min_rows']}")
                else:
                    self.log.warning("  No output file found after scrape")
            if attempt < self.MAX_RETRIES:
                self.log.info(f"  Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
        return False, None

    def _find_output(self, cfg: Dict) -> Optional[str]:
        if "output_csv" in cfg and Path(cfg["output_csv"]).exists():
            return cfg["output_csv"]
        if "output_dir" in cfg and "output_glob" in cfg:
            files = _glob.glob(os.path.join(cfg["output_dir"], cfg["output_glob"]))
            if files:
                return max(files, key=os.path.getmtime)
        return None

print("✅ ListingsAgent defined (Phase 2 ReAct + Phase 3 Fallback)")
