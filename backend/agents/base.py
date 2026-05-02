import json
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from llm import _build_logger, call_llm, parse_llm_json, LLM_PRIMARY
from memory_store import AgentMemory, HEURISTICS


# ── BaseAgent ─────────────────────────────────────────────────────────────────

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name   = name
        self.memory = AgentMemory(name)
        self.log    = _build_logger(name)

    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]: ...

    def decide(
        self,
        prompt:   str,
        context:  Optional[Dict] = None,
        model:    str            = LLM_PRIMARY,
        scope:    Optional[str]  = None,
    ) -> Dict:
        heuristics_block = ""
        try:
            h_text = HEURISTICS.format_for_prompt(self.name, scope=scope)
            if h_text:
                heuristics_block = h_text + "\n\n"
        except Exception:
            pass

        ctx_block = ""
        if context:
            ctx_block = (
                "PIPELINE CONTEXT (current run data):\n"
                + json.dumps(context, indent=2, default=str)
                + "\n\n"
            )

        full_prompt = heuristics_block + ctx_block + prompt
        self.log.debug(f"decide() prompt ({len(full_prompt)} chars):\n{full_prompt[:600]}")

        raw    = call_llm(full_prompt, model=model)
        result = parse_llm_json(raw)

        result.setdefault("thought",    "(no thought provided)")
        result.setdefault("action",     "continue")
        result.setdefault("reason",     "no reason provided")
        result.setdefault("confidence", 0.5)

        self.log.debug(f"decide() result: {result}")
        return result

    def log_decision(self, d: Dict, ctx: str = ""):
        self.memory.remember("decisions", {"decision": d, "context": ctx})
        self.log.info(f"┌─ DECISION [{ctx}]")
        thought = d.get("thought", "")
        if thought and thought != "(no thought provided)":
            for i, line in enumerate(thought.split(". ")):
                prefix = "│  thought   : " if i == 0 else "│             "
                self.log.info(f"{prefix}{line.strip()}.")
        self.log.info(f"│  action     : {d.get('action', '?')}")
        self.log.info(f"│  reason     : {d.get('reason', '?')}")
        self.log.info(f"└─ confidence : {d.get('confidence', '?')}")

    def update_state(self, state: Dict, k: str, v: Any) -> Dict:
        state[k] = v
        self.log.debug(f"State updated — {k}: {str(v)[:120]}")
        return state

    @staticmethod
    def _resolve_python(cwd: str) -> str:
        cwd_path   = Path(cwd)
        candidates = [
            cwd_path / "venv"  / "Scripts" / "python.exe",
            cwd_path / "venv"  / "bin"     / "python",
            cwd_path / ".venv" / "Scripts" / "python.exe",
            cwd_path / ".venv" / "bin"     / "python",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return sys.executable

    def _run_subprocess(
        self, cmd: List[str], cwd: str, timeout: int = 3600,
    ) -> Tuple[bool, str, str]:
        self.log.info(f"  $ {' '.join(cmd)}")
        self.log.info(f"  cwd: {cwd}")
        try:
            r = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
            )
            if r.returncode == 0:
                self.log.info("  ✅ exit 0")
                if r.stdout:
                    self.log.debug(f"  STDOUT: {r.stdout[-500:]}")
            else:
                self.log.error(f"  ❌ exit {r.returncode}")
                self.log.error(f"  STDERR: {r.stderr[-800:]}")
            return r.returncode == 0, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            self.log.error(f"  ❌ TIMEOUT after {timeout}s")
            return False, "", "TimeoutExpired"
        except FileNotFoundError as e:
            self.log.error(f"  ❌ Script not found: {e}")
            return False, "", str(e)
        except Exception as e:
            self.log.error(f"  ❌ Unexpected: {e}")
            return False, "", str(e)

    def _count_rows(self, path: str) -> int:
        try:
            with open(path, errors="ignore") as f:
                n = sum(1 for _ in f) - 1
            self.log.debug(f"Row count [{path}]: {n:,}")
            return max(n, 0)
        except Exception:
            return 0


# ── FallbackMixin ─────────────────────────────────────────────────────────────

class FallbackMixin:
    """
    4-rung degradation ladder for any agent that runs scrapers.

    Rung 1 — fresh scrape         (normal path)
    Rung 2 — cached output < 48h  (stale but usable)
    Rung 3 — stale output any age (last resort real data)
    Rung 4 — synthetic rows       (unblock pipeline only)
    """

    MANUAL_OVERRIDE_DIR  = "Data/manual_override"
    SYNTHETIC_SOURCE_TAG = "synthetic_fallback"
    CACHE_SOFT_LIMIT_H   = 48
    MIN_SYNTHETIC_ROWS   = 5

    def resolve_fallback(
        self,
        name:          str,
        cfg:           Dict,
        health_status: str = "unknown",
        find_output_fn = None,
        count_rows_fn  = None,
    ) -> Tuple[str, Optional[str], str]:
        find   = find_output_fn  or (lambda c: None)
        nrows  = count_rows_fn   or (lambda p: 0)
        log    = getattr(self, "log", _build_logger("FallbackMixin"))

        manual_path = self._find_manual(name)
        if manual_path:
            rows = nrows(manual_path)
            log.info(f"  [Fallback] RUNG-MANUAL — {manual_path} ({rows:,} rows)")
            return "manual", manual_path, f"Manual override file found: {rows:,} rows"

        existing = find(cfg)

        if existing and Path(existing).exists():
            age_h = (time.time() - Path(existing).stat().st_mtime) / 3600
            rows  = nrows(existing)
            if age_h < self.CACHE_SOFT_LIMIT_H and rows >= cfg.get("min_rows", 50):
                log.info(f"  [Fallback] RUNG-2 — cache {age_h:.1f}h old, {rows:,} rows")
                return "cache_soft", existing, f"Cached output {age_h:.1f}h old ({rows:,} rows)"

            if rows > 0:
                log.warning(f"  [Fallback] RUNG-3 — stale cache {age_h:.1f}h old, {rows:,} rows")
                return "cache_stale", existing, f"Stale cache {age_h:.1f}h old ({rows:,} rows) — quality degraded"

        if health_status in ("blocked", "down"):
            synth_path = self._generate_synthetic(name)
            if synth_path:
                log.warning(f"  [Fallback] RUNG-4 — synthetic placeholder at {synth_path}")
                return "synthetic", synth_path, f"Synthetic placeholder rows (site {health_status})"

        log.warning(f"  [Fallback] RUNG-NONE — no fallback available for {name}")
        return "none", None, "No fallback available"

    def _find_manual(self, name: str) -> Optional[str]:
        path = Path(self.MANUAL_OVERRIDE_DIR) / f"{name}_manual.csv"
        if path.exists():
            age_days = (time.time() - path.stat().st_mtime) / 86400
            if age_days < 7:
                return str(path)
        return None

    def _generate_synthetic(self, name: str) -> Optional[str]:
        out_dir = Path("Data/raw_listings/synthetic")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(out_dir / f"{name}_synthetic.csv")

        try:
            govs   = ["Tunis", "Ariana", "Ben Arous", "Sousse", "Sfax", "Nabeul"]
            ptypes = ["Apartment", "House", "Villa", "Land"]
            rows   = []
            for i in range(self.MIN_SYNTHETIC_ROWS):
                rows.append({
                    "listing_id":       f"SYNTH_{name}_{i:04d}",
                    "source":           self.SYNTHETIC_SOURCE_TAG,
                    "title":            f"Synthetic listing {i+1} — pipeline fallback",
                    "property_type":    ptypes[i % len(ptypes)],
                    "transaction_type": "Sale",
                    "price":            np.nan,
                    "currency":         "TND",
                    "surface_m2":       np.nan,
                    "governorate":      govs[i % len(govs)],
                    "city":             np.nan,
                    "description":      f"SYNTHETIC FALLBACK ROW — scraper {name} unavailable.",
                    "image_count":      0,
                    "country":          "Tunisia",
                    "is_synthetic":     True,
                })
            pd.DataFrame(rows).to_csv(out_path, index=False)
            return out_path
        except Exception as e:
            log = getattr(self, "log", _build_logger("FallbackMixin"))
            log.error(f"Synthetic generation failed for {name}: {e}")
            return None
