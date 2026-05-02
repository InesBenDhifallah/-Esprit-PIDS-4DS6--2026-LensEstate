import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from base import BaseAgent, FallbackMixin
from llm import call_llm, parse_llm_json
from config import (
    BNB_CWD, BNB_SCRIPT, BNB_OUTPUT_CSV, BNB_OUTPUT_JSON,
    HOUNI_CWD, HOUNI_SCRIPT, HOUNI_OUTPUT_CSV,
)


class ArticlesAgent(BaseAgent, FallbackMixin):
    """
    Runs BnB and Houni blog scrapers.
    Runs FIRST in the pipeline — fast, non-blocking.
    """

    SCRAPERS = {
        "bnb": {
            "cwd"          : BNB_CWD,
            "script"       : BNB_SCRIPT,
            "output_csv"   : BNB_OUTPUT_CSV,
            "output_json"  : BNB_OUTPUT_JSON,
            "min_rows"     : 10,
            "max_age_hours": 6,
            "timeout"      : 600,
        },
        "houni": {
            "cwd"          : HOUNI_CWD,
            "script"       : HOUNI_SCRIPT,
            "args"         : [],
            "output_csv"   : HOUNI_OUTPUT_CSV,
            "min_rows"     : 10,
            "max_age_hours": 6,
            "timeout"      : 600,
        },
    }
    MAX_RECENT_FAILURES = 3
    MAX_RETRIES         = 2
    BACKOFF_SECONDS     = 15
    MAX_REACT_STEPS     = 10

    def __init__(self):
        super().__init__("ArticlesAgent")

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log.info("=" * 60)
        self.log.info("ArticlesAgent — starting (ReAct + Fallback)")
        self.log.info("=" * 60)
        self.memory.clear()
        self.memory.set("action", "collect_articles")

        knowledge = self.memory.recall_knowledge()
        if knowledge:
            self.log.info(f"  Semantic knowledge: {list(knowledge.keys())}")

        collected, results = self._react_loop()
        merged_path = self._merge_articles(collected)

        state = self.update_state(state, "articles_raw_paths",   collected)
        state = self.update_state(state, "articles_results",     results)
        state = self.update_state(state, "merged_articles_path", merged_path or "")

        self.log.info(f"\nArticlesAgent done — {len(collected)} sources collected")
        if merged_path:
            self.log.info(f"  merged → {merged_path}")
        return state

    def _react_loop(self) -> Tuple[List[str], Dict]:
        collected: List[str] = []
        results:   Dict      = {}
        handled:   set       = set()

        scraper_summary = {
            name: self._inspect_scraper(name, cfg)
            for name, cfg in self.SCRAPERS.items()
        }
        knowledge = self.memory.recall_knowledge()

        system_context = (
            "You are ArticlesAgent for LensEstate, a Tunisian real estate platform.\n"
            "Manage two article blog scrapers: bnb, houni.\n"
            "Articles are non-blocking — pipeline continues even if both fail.\n\n"
            "Available tools (call ONE per step):\n"
            "  inspect_scraper(name)         — output age, rows, failure history\n"
            "  run_scraper(name)             — execute subprocess\n"
            "  skip_scraper(name, reason)    — use cache or skip\n"
            "  activate_fallback(name)       — trigger degradation ladder\n"
            "  finish()                      — all scrapers handled\n\n"
            "Rules:\n"
            "  SKIP  if output fresh (< max_age_hours) AND rows >= min_rows\n"
            "  SKIP  if recent_failures >= 3 AND no valid output\n"
            "  RUN   if output stale, missing, or below min_rows\n"
            "  FALLBACK if scraper failed and cache exists\n\n"
            f"Scraper states:\n{json.dumps(scraper_summary, indent=2)}\n\n"
            f"Semantic knowledge from past runs:\n{json.dumps(knowledge, indent=2)}\n\n"
            'Reply ONLY JSON: {"thought": "reasoning", "tool": "name", "args": {}}'
        )

        messages = [{"role": "user", "content": system_context}]

        for step in range(self.MAX_REACT_STEPS):
            self.log.info(f"\n  [ReAct step {step+1}/{self.MAX_REACT_STEPS}]")

            recent = messages[-3:] if len(messages) > 3 else messages
            prompt = "\n---\n".join(m["content"] for m in recent)
            raw    = call_llm(prompt, max_tokens=512)
            parsed = parse_llm_json(raw)

            thought = parsed.get("thought", "")
            tool    = parsed.get("tool", "finish")
            args    = parsed.get("args", {})

            self.log.info(f"  thought : {thought[:200]}")
            self.log.info(f"  tool    : {tool}  args={args}")

            if tool == "inspect_scraper":
                name        = args.get("name", "")
                result_data = self._inspect_scraper(name, self.SCRAPERS.get(name, {}))
                tool_result = json.dumps(result_data)
                self.log.info(f"  → {tool_result[:250]}")

            elif tool == "run_scraper":
                name = args.get("name", "")
                cfg  = self.SCRAPERS.get(name)
                if not cfg:
                    tool_result = f"Unknown scraper: {name}"
                else:
                    success, path = self._run_with_retry(name, cfg)
                    if success and path:
                        quality = self._assess_quality(path)
                        collected.append(path)
                        results[name] = {"status": "success", "path": path, **quality}
                        self.memory.remember("successes", {"scraper": name, **quality})
                        self.memory.know(f"{name}.typical_rows", quality["total"])
                        tool_result = f"Success — {quality['total']} articles"
                        self.log.info(f"  ✅ {name} → {tool_result}")
                    else:
                        self.log.warning(f"  {name} failed — activating fallback")
                        rung, fpath, explanation = self.resolve_fallback(
                            name, cfg,
                            health_status="unknown",
                            find_output_fn=lambda c: c.get("output_csv") if Path(c.get("output_csv", "")).exists() else None,
                            count_rows_fn=self._count_rows,
                        )
                        if fpath:
                            collected.append(fpath)
                            results[name] = {"status": "fallback", "fallback_rung": rung, "path": fpath, "explanation": explanation}
                            tool_result = f"Failed → fallback {rung}: {explanation}"
                        else:
                            results[name] = {"status": "failed"}
                            self.memory.remember("failures", {"scraper": name, "reason": "retries_exhausted_no_fallback"})
                            tool_result = "Failed — no fallback available"
                    handled.add(name)

            elif tool == "activate_fallback":
                name = args.get("name", "")
                cfg  = self.SCRAPERS.get(name, {})
                rung, fpath, explanation = self.resolve_fallback(
                    name, cfg,
                    health_status="unknown",
                    find_output_fn=lambda c: c.get("output_csv") if Path(c.get("output_csv", "")).exists() else None,
                    count_rows_fn=self._count_rows,
                )
                if fpath:
                    collected.append(fpath)
                    results[name] = {"status": "fallback", "fallback_rung": rung, "path": fpath, "explanation": explanation}
                    tool_result = f"Fallback {rung}: {explanation}"
                else:
                    results[name] = {"status": "skipped", "reason": "no_fallback"}
                    tool_result = "No fallback available — skipping"
                handled.add(name)
                self.log.info(f"  ⚠️  {name} → {tool_result}")

            elif tool == "skip_scraper":
                name   = args.get("name", "")
                reason = args.get("reason", "")
                cfg    = self.SCRAPERS.get(name, {})
                existing = cfg.get("output_csv", "")
                if existing and Path(existing).exists():
                    collected.append(existing)
                    results[name] = {"status": "skipped", "reason": reason, "path": existing}
                    tool_result = f"Skipped — using cache: {self._count_rows(existing)} rows"
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

        for name, cfg in self.SCRAPERS.items():
            if name not in handled and name not in results:
                self.log.warning(f"  Safety net: {name}")
                skip, reason = self._should_skip_fallback(name, cfg)
                if skip:
                    existing = cfg.get("output_csv", "")
                    if existing and Path(existing).exists():
                        collected.append(existing)
                    results[name] = {"status": "skipped", "reason": reason}
                else:
                    success, path = self._run_with_retry(name, cfg)
                    if success and path:
                        quality = self._assess_quality(path)
                        collected.append(path)
                        results[name] = {"status": "success", "path": path, **quality}
                        self.memory.remember("successes", {"scraper": name, **quality})
                    else:
                        results[name] = {"status": "failed"}
                        self.memory.remember("failures", {"scraper": name, "reason": "safety_net_failed"})

        return collected, results

    def _inspect_scraper(self, name: str, cfg: Dict) -> Dict:
        csv_path      = cfg.get("output_csv", "")
        max_age_hours = cfg.get("max_age_hours", 6)
        min_rows      = cfg.get("min_rows", 10)

        output_info = {"exists": False, "rows": 0, "age_hours": None, "fresh": False}
        if csv_path and Path(csv_path).exists():
            import os
            age_h = (time.time() - os.path.getmtime(csv_path)) / 3600
            rows  = self._count_rows(csv_path)
            output_info = {
                "exists":    True,
                "rows":      rows,
                "age_hours": round(age_h, 1),
                "fresh":     age_h < max_age_hours and rows >= min_rows,
            }

        recent_failures = [
            f for f in self.memory.recall("failures", 20)
            if f.get("scraper") == name
        ]
        typical_rows = self.memory.recall_knowledge(f"{name}.typical_rows")

        return {
            "scraper":         name,
            "min_rows":        min_rows,
            "max_age_hours":   max_age_hours,
            "output":          output_info,
            "recent_failures": len(recent_failures),
            "last_failure":    recent_failures[-1] if recent_failures else None,
            "typical_rows":    typical_rows,
            "manual_override": self._find_manual(name) is not None,
        }

    def _should_skip_fallback(self, name: str, cfg: Dict) -> Tuple[bool, str]:
        import os
        csv_path      = cfg.get("output_csv", "")
        max_age_hours = cfg.get("max_age_hours", 6)
        if Path(csv_path).exists():
            age_h = (time.time() - os.path.getmtime(csv_path)) / 3600
            rows  = self._count_rows(csv_path)
            if age_h < max_age_hours and rows >= cfg["min_rows"]:
                return True, f"Fresh ({age_h:.1f}h, {rows} rows)"
        recent_fail = [f for f in self.memory.recall("failures", 20) if f.get("scraper") == name]
        if len(recent_fail) >= self.MAX_RECENT_FAILURES:
            return True, f"Failed {len(recent_fail)}x recently"
        return False, "Output missing or stale"

    def _run_with_retry(self, name: str, cfg: Dict) -> Tuple[bool, Optional[str]]:
        backoff = self.BACKOFF_SECONDS
        python  = self._resolve_python(cfg["cwd"])
        self.log.info(f"  python : {python}")
        cmd = [python, cfg["script"]] + cfg.get("args", [])
        for attempt in range(1, self.MAX_RETRIES + 1):
            self.log.info(f"  Attempt {attempt}/{self.MAX_RETRIES}")
            success, _, _ = self._run_subprocess(cmd, cfg["cwd"], cfg.get("timeout", 600))
            if success:
                path = cfg["output_csv"]
                if Path(path).exists():
                    rows = self._count_rows(path)
                    if rows >= cfg["min_rows"]:
                        return True, path
                    self.log.warning(f"  Too few rows: {rows} < {cfg['min_rows']}")
                else:
                    self.log.warning(f"  Output not found: {path}")
            if attempt < self.MAX_RETRIES:
                self.log.info(f"  Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
        return False, None

    def _assess_quality(self, path: str) -> Dict:
        try:
            df    = pd.read_csv(path, encoding="utf-8")
            total = len(df)
            empty = df["content"].isna().mean() if "content" in df.columns else 0.0
            dupes = df.duplicated(subset=["title"]).mean() if "title" in df.columns else 0.0
            short = (df["content"].fillna("").str.split().str.len() < 50).mean() \
                    if "content" in df.columns else 0.0
            return {
                "total":     total,
                "empty_pct": round(empty, 3),
                "dupe_pct":  round(dupes, 3),
                "short_pct": round(short, 3),
            }
        except Exception as e:
            self.log.error(f"Quality assessment error: {e}")
            return {"total": 0, "empty_pct": 1.0, "dupe_pct": 0.0, "short_pct": 1.0}

    def _merge_articles(self, paths: List[str]) -> Optional[str]:
        dfs = []
        for path in paths:
            try:
                source = "bnb_blog" if "bnb" in path.lower() else "houni_blog"
                enc    = "latin-1" if "houni" in path.lower() else "utf-8"
                df     = pd.read_csv(path, encoding=enc)
                if "houni" in path.lower():
                    def fix(t):
                        try:    return t.encode("latin-1").decode("utf-8")
                        except: return t
                    df = df.apply(lambda c: c.map(fix) if c.dtype == object else c)
                if "title" in df.columns and "content" in df.columns:
                    df = df[["title", "content"]].assign(source=source)
                    dfs.append(df)
                    self.log.info(f"  Loaded {len(df)} articles from {source}")
            except Exception as e:
                self.log.error(f"Failed to load {path}: {e}")
        if not dfs:
            self.log.warning("No article DataFrames to merge")
            return None
        merged = pd.concat(dfs, ignore_index=True)
        merged.insert(0, "article_id", range(1, len(merged) + 1))
        out = "Data/raw_articles/merged_articles.csv"
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(out, index=False)
        self.log.info(f"  Articles merged: {len(merged)} total → {out}")
        return out
