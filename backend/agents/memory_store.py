import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm import _build_logger, call_llm, parse_llm_json, LLM_FALLBACK


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ── AgentMemory ───────────────────────────────────────────────────────────────

class AgentMemory:
    """
    Two-tier memory system for each agent.

    Tier 1 — Episodic (short-term, per-run scratchpad):
        self.short  — cleared at the start of every run() call.

    Tier 2 — Semantic (long-term, persisted to disk as JSON):
        self.long   — survives across runs.
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

    def remember(self, cat: str, entry: Dict):
        entry["ts"] = _now()
        with self._lock:
            self.long.setdefault(cat, []).append(entry)
            if len(self.long[cat]) > 200:
                self.long[cat] = self.long[cat][-200:]
            self._save()
        self._log.debug(f"[MEMORY:{cat}] {entry}")

    def recall(self, cat: str, n: int = 10) -> List[Dict]:
        return self.long.get(cat, [])[-n:]

    def know(self, key: str, value: Any):
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

    def set_lt(self, k: str, v: Any):
        with self._lock:
            self.long[k] = v
            self._save()

    def get_lt(self, k: str, d=None):
        return self.long.get(k, d)

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
        return {
            "name":       self.name,
            "successes":  len(self.long.get("successes", [])),
            "failures":   len(self.long.get("failures", [])),
            "decisions":  len(self.long.get("decisions", [])),
            "knowledge":  list(self.long.get("knowledge", {}).keys()),
        }


# ── HeuristicsStore ───────────────────────────────────────────────────────────

HEURISTICS_PATH = "memory/heuristics.json"


class HeuristicsStore:
    """
    Procedural memory — durable rules the LLM has learned from past runs.
    Stored in memory/heuristics.json.
    """

    def __init__(self, path: str = HEURISTICS_PATH):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._log  = _build_logger("HeuristicsStore")
        self._data : List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self._log.warning(f"Could not load heuristics: {e}")
        return []

    def _save(self):
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)

    def get_all(self) -> List[Dict]:
        return list(self._data)

    def get_for(self, agent_name: str, scope: str = None) -> List[str]:
        rules = []
        for h in self._data:
            applies = h.get("applies_to", [])
            h_scope = h.get("scope", "global")
            if agent_name in applies or "global" in applies:
                if scope is None or h_scope in (scope, "global"):
                    rules.append(h["rule"])
        return rules

    def add(
        self,
        scope:       str,
        rule:        str,
        confidence:  float     = 0.75,
        applies_to:  List[str] = None,
        source:      str       = "manual",
    ) -> Dict:
        entry = {
            "id":         f"h_{len(self._data)+1:03d}",
            "scope":      scope,
            "rule":       rule,
            "confidence": round(confidence, 2),
            "source":     source,
            "created_at": _now(),
            "applies_to": applies_to or ["global"],
        }
        self._data.append(entry)
        self._save()
        self._log.info(f"Heuristic added [{entry['id']}] scope={scope}: {rule[:80]}")
        return entry

    def remove(self, heuristic_id: str) -> bool:
        before = len(self._data)
        self._data = [h for h in self._data if h["id"] != heuristic_id]
        if len(self._data) < before:
            self._save()
            self._log.info(f"Heuristic {heuristic_id} removed")
            return True
        return False

    def format_for_prompt(self, agent_name: str, scope: str = None) -> str:
        rules = self.get_for(agent_name, scope)
        if not rules:
            return ""
        lines = "\n".join(f"  - {r}" for r in rules)
        return f"Learned heuristics (apply these when reasoning):\n{lines}"

    def summary(self) -> str:
        return (
            f"{len(self._data)} heuristics across "
            f"{len(set(h.get('scope','global') for h in self._data))} scopes"
        )


# Global singleton
HEURISTICS = HeuristicsStore()
