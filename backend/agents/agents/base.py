class AgentMemory:
    """
    Two-tier memory system for each agent.

    Tier 1 — Episodic (short-term, per-run scratchpad):
        self.short  — cleared at the start of every run() call.
        Stores the current run's action, result, errors, warnings.

    Tier 2 — Semantic (long-term, persisted to disk as JSON):
        self.long   — survives across runs. Contains:
            successes       list  — every successful scrape/operation
            failures        list  — every failure with reason + timestamp
            decisions       list  — every LLM routing decision with thought
            quality         list  — quality metrics per run
            schema_repairs  list  — LLM-inferred column mappings (StandardizationAgent)
            suspicious_flags list — LLM anomaly detection results (CleaningAgent)
            knowledge        dict — free-form cross-run facts agents can read/write
                                    e.g. {"mubawab": {"typical_rows": 1200,
                                                       "known_issues": ["slow sundays"]}}

    The `knowledge` sub-dict is the semantic memory store. Agents read it
    at the start of their ReAct loop and write to it when they discover
    something durable (a typical row range, a recurring failure pattern, etc.).
    """

    def __init__(self, name: str, state_dir: str = "memory/state/"):
        self.name   = name
        self._dir   = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock  = threading.Lock()
        self._path  = self._dir / f"{name}_memory.json"
        self.short  : Dict[str, Any] = {
            "action": None, "result": None, "errors": [], "warnings": []
        }
        self.long   : Dict[str, Any] = self._load()
        self._log   = _build_logger(f"Memory.{name}")

    # ── Episodic (short-term) ─────────────────────────────────────────────────
    def set(self, k: str, v: Any):
        self.short[k] = v

    def get(self, k: str, d=None):
        return self.short.get(k, d)

    def add_error(self, e: str):
        self.short["errors"].append({"ts": _now(), "msg": e})
        self._log.debug(f"[ERROR] {e}")

    def add_warning(self, w: str):
        self.short["warnings"].append({"ts": _now(), "msg": w})
        self._log.debug(f"[WARNING] {w}")

    def clear(self):
        self.short = {"action": None, "result": None, "errors": [], "warnings": []}

    # ── Semantic (long-term event log) ────────────────────────────────────────
    def remember(self, cat: str, entry: Dict):
        """Append an event to a named category list (capped at 200 entries)."""
        entry["ts"] = _now()
        with self._lock:
            self.long.setdefault(cat, []).append(entry)
            if len(self.long[cat]) > 200:
                self.long[cat] = self.long[cat][-200:]
            self._save()
        self._log.debug(f"[MEMORY:{cat}] {entry}")

    def recall(self, cat: str, n: int = 10) -> List[Dict]:
        """Return the last n entries from a category."""
        return self.long.get(cat, [])[-n:]

    # ── Semantic knowledge store (free-form facts) ────────────────────────────
    def know(self, key: str, value: Any):
        """
        Write a durable fact to the knowledge store.
        key   — dot-separated path, e.g. "mubawab.typical_rows"
        value — any JSON-serialisable value

        Example:
            agent.memory.know("mubawab.typical_rows", 1250)
            agent.memory.know("mubawab.known_issues", ["slow on sundays"])
        """
        parts = key.split(".")
        with self._lock:
            node = self.long.setdefault("knowledge", {})
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value
            self.long["knowledge"]["_last_updated"] = _now()
            self._save()
        self._log.debug(f"[KNOWLEDGE] {key} = {value}")

    def recall_knowledge(self, key: str = None) -> Any:
        """
        Read from the knowledge store.
        key=None  → return the entire knowledge dict
        key="mubawab.typical_rows" → return that specific value, or None
        """
        store = self.long.get("knowledge", {})
        if key is None:
            return store
        parts = key.split(".")
        node  = store
        for part in parts:
            if not isinstance(node, dict):
                return None
            node = node.get(part)
        return node

    # ── Long-term scalar setters (backward compat) ─────────────────────────────
    def set_lt(self, k: str, v: Any):
        with self._lock:
            self.long[k] = v
            self._save()

    def get_lt(self, k: str, d=None):
        return self.long.get(k, d)

    # ── Persistence ───────────────────────────────────────────────────────────
    def _load(self) -> Dict:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "successes":        [],
            "failures":         [],
            "decisions":        [],
            "quality":          [],
            "schema_repairs":   [],
            "suspicious_flags": [],
            "knowledge":        {},
        }

    def _save(self):
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.long, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)

    def summary(self) -> Dict:
        """Return a compact summary for logging/debugging."""
        return {
            "name":       self.name,
            "successes":  len(self.long.get("successes", [])),
            "failures":   len(self.long.get("failures", [])),
            "decisions":  len(self.long.get("decisions", [])),
            "knowledge":  list(self.long.get("knowledge", {}).keys()),
        }

print("✅ AgentMemory defined (episodic + semantic knowledge store)")

# ─────────────────────────────────────────────────────────────────────────────
# CELL 113 — BaseAgent  (Phase 4 update: heuristics injection in decide())
# ─────────────────────────────────────────────────────────────────────────────

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name   = name
        self.memory = AgentMemory(name)
        self.log    = _build_logger(name)

    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]: ...

    # ── LLM reasoning ─────────────────────────────────────────────────────────
    def decide(
        self,
        prompt:       str,
        context:      Optional[Dict] = None,
        model:        str            = LLM_PRIMARY,
        scope:        Optional[str]  = None,
    ) -> Dict:
        """
        Ask the LLM to reason about a situation and return a structured decision.

        Phase 4: automatically prepends any relevant heuristics from
        HeuristicsStore so the LLM benefits from past-run experience.

        Args:
            prompt   — the question / task for the LLM
            context  — structured data serialised as JSON and prepended
            model    — which OpenRouter model to use
            scope    — optional scraper name to filter heuristics (e.g. 'mubawab')

        Returns dict always containing: thought, action, reason, confidence
        """
        # ── Heuristics block ──────────────────────────────────────────────
        heuristics_block = ""
        try:
            # HEURISTICS is the global singleton defined in Cell 119b
            h_text = HEURISTICS.format_for_prompt(self.name, scope=scope)
            if h_text:
                heuristics_block = h_text + "\n\n"
        except NameError:
            pass   # HeuristicsStore not yet defined (early cells running alone)

        # ── Context block ─────────────────────────────────────────────────
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
        """Persist decision to memory and print a structured log block."""
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

    # ── State helpers ──────────────────────────────────────────────────────────
    def update_state(self, state: Dict, k: str, v: Any) -> Dict:
        state[k] = v
        self.log.debug(f"State updated — {k}: {str(v)[:120]}")
        return state

    # ── Subprocess helpers (unchanged) ─────────────────────────────────────────
    @staticmethod
    def _resolve_python(cwd: str) -> str:
        from pathlib import Path as _P
        cwd_path   = _P(cwd)
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

print("✅ BaseAgent defined (Phase 4: heuristics injected into every decide() call)")

class FallbackMixin:
    """
    Mixin that adds the 4-rung degradation ladder to any agent that runs scrapers.

    Rung 1 — fresh scrape         (normal path)
    Rung 2 — cached output < 48h  (stale but usable)
    Rung 3 — stale output any age (last resort real data)
    Rung 4 — synthetic rows       (unblock pipeline only; stripped before model CSV)

    Usage:
        class ListingsAgent(BaseAgent, FallbackMixin): ...
        # then call self.resolve_fallback(name, cfg, health_status) inside ReAct loop
    """

    MANUAL_OVERRIDE_DIR  = "Data/manual_override"
    SYNTHETIC_SOURCE_TAG = "synthetic_fallback"
    CACHE_SOFT_LIMIT_H   = 48    # rung 2 threshold
    MIN_SYNTHETIC_ROWS   = 5     # rows to generate on rung 4

    def resolve_fallback(
        self,
        name:          str,
        cfg:           Dict,
        health_status: str = "unknown",
        find_output_fn = None,
        count_rows_fn  = None,
    ) -> Tuple[str, Optional[str], str]:
        """
        Walk the degradation ladder and return:
            (rung_label, path_or_None, explanation)

        rung_label one of: "manual", "cache_soft", "cache_stale", "synthetic", "none"
        """
        find   = find_output_fn  or (lambda c: None)
        nrows  = count_rows_fn   or (lambda p: 0)
        log    = getattr(self, "log", _build_logger("FallbackMixin"))

        # ── Manual override (highest priority) ────────────────────────────
        manual_path = self._find_manual(name)
        if manual_path:
            rows = nrows(manual_path)
            log.info(f"  [Fallback] RUNG-MANUAL — {manual_path} ({rows:,} rows)")
            return "manual", manual_path, f"Manual override file found: {rows:,} rows"

        existing = find(cfg)

        # ── Rung 2: cache < 48h ───────────────────────────────────────────
        if existing and Path(existing).exists():
            age_h = (time.time() - os.path.getmtime(existing)) / 3600
            rows  = nrows(existing)
            if age_h < self.CACHE_SOFT_LIMIT_H and rows >= cfg.get("min_rows", 50):
                log.info(f"  [Fallback] RUNG-2 — cache {age_h:.1f}h old, {rows:,} rows")
                return "cache_soft", existing, f"Cached output {age_h:.1f}h old ({rows:,} rows)"

            # ── Rung 3: stale cache any age ───────────────────────────────
            if rows > 0:
                log.warning(f"  [Fallback] RUNG-3 — stale cache {age_h:.1f}h old, {rows:,} rows")
                return "cache_stale", existing, f"Stale cache {age_h:.1f}h old ({rows:,} rows) — quality degraded"

        # ── Rung 4: synthetic rows ────────────────────────────────────────
        # Only generate if site is blocked/down — not if we've never scraped it
        if health_status in ("blocked", "down"):
            synth_path = self._generate_synthetic(name)
            if synth_path:
                log.warning(f"  [Fallback] RUNG-4 — synthetic placeholder at {synth_path}")
                return "synthetic", synth_path, f"Synthetic placeholder rows (site {health_status})"

        log.warning(f"  [Fallback] RUNG-NONE — no fallback available for {name}")
        return "none", None, "No fallback available"

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _find_manual(self, name: str) -> Optional[str]:
        """Check Data/manual_override/{name}_manual.csv (< 7 days old)."""
        path = Path(self.MANUAL_OVERRIDE_DIR) / f"{name}_manual.csv"
        if path.exists():
            age_days = (time.time() - os.path.getmtime(str(path))) / 86400
            if age_days < 7:
                return str(path)
        return None

    def _generate_synthetic(self, name: str) -> Optional[str]:
        """
        Generate a minimal set of clearly-tagged synthetic rows.
        These are placeholder rows only — stripped before the final model CSV.
        Every field is either a realistic Tunisian value or NaN.
        """
        import numpy as _np

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
                    "price":            _np.nan,
                    "currency":         "TND",
                    "surface_m2":       _np.nan,
                    "governorate":      govs[i % len(govs)],
                    "city":             _np.nan,
                    "description":      f"SYNTHETIC FALLBACK ROW — scraper {name} unavailable.",
                    "image_count":      0,
                    "country":          "Tunisia",
                    "is_synthetic":     True,
                })
            pd.DataFrame(rows).to_csv(out_path, index=False)
            return out_path
        except Exception as e:
            _log = getattr(self, "log", _build_logger("FallbackMixin"))
            _log.error(f"Synthetic generation failed for {name}: {e}")
            return None




