# ─────────────────────────────────────────────────────────────────────────────
# CELL 114b — Phase 3: ScraperHealthAgent + FallbackMixin
# INSERT this cell between Cell 114 (ArticlesAgent) and Cell 115 (ListingsAgent)
# ─────────────────────────────────────────────────────────────────────────────

import glob as _glob
import shutil
import requests as _requests

# ── Scraper health check ──────────────────────────────────────────────────────

class ScraperHealthAgent(BaseAgent):
    """
    Pre-flight agent — runs before ListingsAgent.
    Sends a lightweight HEAD request to each target website and classifies
    the failure mode so ListingsAgent can reason about it:

      healthy      — site responds 200/30x
      blocked      — 403/429 (IP block / rate limit — wait or rotate)
      down         — 5xx or connection error (site issue — retry later)
      unknown      — any other status

    Result stored in state["scraper_health"] for the LLM to read.
    """

    TARGETS = {
        "mubawab"        : "https://www.mubawab.tn",
        "tayara"         : "https://www.tayara.tn",
        "tunisie_annonce": "https://www.tunisie-annonce.com",
    }
    TIMEOUT = 8   # seconds per request

    def __init__(self):
        super().__init__("ScraperHealthAgent")

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log.info("=" * 60)
        self.log.info("ScraperHealthAgent — pre-flight checks")
        self.log.info("=" * 60)

        health: Dict[str, Dict] = {}

        for name, url in self.TARGETS.items():
            self.log.info(f"  Checking {name} ({url}) ...")
            status, detail = self._check(url)
            health[name] = {"status": status, "detail": detail, "url": url}

            icon = {"healthy": "✅", "blocked": "🚫", "down": "❌", "unknown": "⚠️"}.get(status, "?")
            self.log.info(f"  {icon}  {name:<20} → {status}  ({detail})")

        # LLM summary — one sentence of context for downstream agents
        summary_prompt = (
            f"Scraper pre-flight results: {json.dumps(health)}.\n"
            f"Summarize in one sentence what this means for running the scrapers.\n"
            'Return ONLY JSON: {"thought": "...", "summary": "one sentence"}'
        )
        dec     = self.decide(summary_prompt)
        summary = dec.get("summary", "Health check complete.")
        self.log.info(f"\n  LLM summary: {summary}")

        state = self.update_state(state, "scraper_health",         health)
        state = self.update_state(state, "scraper_health_summary", summary)
        return state

    def _check(self, url: str) -> Tuple[str, str]:
        try:
            r = _requests.head(url, timeout=self.TIMEOUT,
                               headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
            code = r.status_code
            if code in (200, 301, 302, 303, 307, 308):
                return "healthy", f"HTTP {code}"
            if code in (403, 429):
                return "blocked", f"HTTP {code} — IP block or rate limit"
            if code >= 500:
                return "down", f"HTTP {code} — server error"
            return "unknown", f"HTTP {code}"
        except _requests.exceptions.ConnectionError:
            return "down", "connection refused"
        except _requests.exceptions.Timeout:
            return "down", f"timeout after {self.TIMEOUT}s"
        except Exception as e:
            return "unknown", str(e)[:80]


print("✅ ScraperHealthAgent defined")

