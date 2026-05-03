import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Dict

import requests

from config import (
    OPENROUTER_API_KEY, TOKEN_FACTORY_API_KEY,
    OPENROUTER_URL, TOKEN_FACTORY_URL,
    LLM_PRIMARY, LLM_FALLBACK, LLM_FALLBACK_SMALL,
)

# ── Logging ───────────────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)


def _build_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s | %(name)-26s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    fh = logging.FileHandler("logs/pipeline.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


_root = logging.getLogger()
_root.setLevel(logging.DEBUG)

# ── LLM system prompt ─────────────────────────────────────────────────────────
_LLM_SYSTEM_PROMPT = (
    "You are a data-pipeline reasoning agent for LensEstate, "
    "a Tunisian real-estate platform. "
    "Always reply with a single valid JSON object and nothing else. "
    "No markdown, no prose outside the JSON. "
    "Include a 'thought' field where you reason step-by-step "
    "before committing to an action."
)

_llm_log = _build_logger("LLM")

OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type":  "application/json",
    "HTTP-Referer":  "https://github.com/lenstate-pipeline",
    "X-Title":       "LensEstate Pipeline",
}

TOKEN_FACTORY_HEADERS = {
    "Authorization": f"Bearer {TOKEN_FACTORY_API_KEY}",
    "Content-Type":  "application/json",
}


def _post_openrouter(model: str, prompt: str, max_tokens: int, timeout: int) -> requests.Response:
    return requests.post(
        OPENROUTER_URL,
        headers=OPENROUTER_HEADERS,
        json={
            "model":       model,
            "max_tokens":  max_tokens,
            "temperature": 0.15,
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        },
        timeout=timeout,
    )


def _post_token_factory(model: str, prompt: str, max_tokens: int, timeout: int) -> requests.Response:
    return requests.post(
        TOKEN_FACTORY_URL,
        headers=TOKEN_FACTORY_HEADERS,
        json={
            "model":             model,
            "max_tokens":        max_tokens,
            "temperature":       0.15,
            "top_p":             0.9,
            "frequency_penalty": 0.0,
            "presence_penalty":  0.0,
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        },
        timeout=timeout,
        verify=False,
    )


def call_llm(
    prompt:     str,
    model:      str = LLM_PRIMARY,
    max_tokens: int = 512,
    retries:    int = 3,
    timeout:    int = 60,
) -> str:
    primary_key_ok  = OPENROUTER_API_KEY  != "YOUR_OPENROUTER_KEY_HERE"
    fallback_key_ok = TOKEN_FACTORY_API_KEY != "YOUR_TOKEN_FACTORY_KEY_HERE"

    if not primary_key_ok:
        _llm_log.warning("OpenRouter key not set -- will attempt Token Factory directly")

    use_token_factory = not primary_key_ok or model.startswith("hosted_vllm/")
    current_model     = LLM_FALLBACK if use_token_factory else model
    backend           = "token_factory" if use_token_factory else "openrouter"
    backoff           = 5

    for attempt in range(1, retries + 2):
        _llm_log.debug(f"LLM attempt {attempt} | backend={backend} | model={current_model}")
        try:
            if backend == "openrouter":
                resp = _post_openrouter(current_model, prompt, max_tokens, timeout)
            else:
                if not fallback_key_ok:
                    _llm_log.error("Token Factory key not set -- cannot call fallback")
                    break
                resp = _post_token_factory(current_model, prompt, max_tokens, timeout)

            if resp.status_code == 429:
                if backend == "openrouter":
                    _llm_log.warning(f"OpenRouter rate-limited -- switching to Token Factory ({LLM_FALLBACK})")
                    backend       = "token_factory"
                    current_model = LLM_FALLBACK
                else:
                    _llm_log.warning(f"Token Factory rate-limited -- waiting {backoff}s")
                    time.sleep(backoff)
                    backoff *= 2
                continue

            if resp.status_code >= 500:
                _llm_log.warning(f"Server error {resp.status_code} ({backend}) -- waiting {backoff}s")
                time.sleep(backoff)
                backoff *= 2
                if backend == "openrouter" and attempt >= 2:
                    _llm_log.warning("Escalating to Token Factory after repeated 5xx")
                    backend       = "token_factory"
                    current_model = LLM_FALLBACK
                continue

            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            _llm_log.debug(f"LLM raw response ({len(raw)} chars): {raw[:300]}")
            return raw

        except requests.exceptions.SSLError:
            _llm_log.warning("SSL error on Token Factory")
        except requests.exceptions.Timeout:
            _llm_log.warning(f"LLM timeout after {timeout}s (attempt {attempt})")
        except requests.exceptions.ConnectionError as e:
            _llm_log.warning(f"LLM connection error (attempt {attempt}): {e}")
        except Exception as e:
            _llm_log.error(f"Unexpected LLM error (attempt {attempt}): {e}")

        if attempt < retries + 1:
            time.sleep(backoff)
            backoff *= 2

    if fallback_key_ok and current_model != LLM_FALLBACK_SMALL:
        _llm_log.warning(f"Trying last-resort model {LLM_FALLBACK_SMALL}")
        try:
            resp = _post_token_factory(LLM_FALLBACK_SMALL, prompt, min(max_tokens, 256), timeout)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            return raw
        except Exception as e:
            _llm_log.error(f"Last-resort model also failed: {e}")

    _llm_log.error("All LLM paths exhausted -- returning safe deterministic fallback")
    return json.dumps({
        "thought":    "All LLM paths exhausted. Defaulting to safe continue.",
        "action":     "continue",
        "reason":     "llm_unavailable",
        "confidence": 0.3,
    })


def parse_llm_json(raw: str) -> Dict:
    try:
        clean = raw.strip()
        if "```" in clean:
            parts = clean.split("```")
            for part in parts:
                if part.startswith("json"):
                    part = part[4:]
                part = part.strip()
                if part.startswith("{"):
                    clean = part
                    break
        m = re.search(r'\{.*\}', clean, re.DOTALL)
        if m:
            return json.loads(m.group())
        return json.loads(clean)
    except Exception:
        _llm_log.warning(f"JSON parse failed on: {raw[:200]}")
        return {
            "thought":    "Could not parse LLM response as JSON.",
            "action":     "continue",
            "reason":     "parse_error",
            "confidence": 0.3,
        }


def test_llm_connection() -> bool:
    print("Testing LLM connection...")
    print(f"  Primary  (OpenRouter)    : {LLM_PRIMARY}")
    print(f"  Fallback (Token Factory) : {LLM_FALLBACK}")
    print(f"  OpenRouter key   : {'set' if OPENROUTER_API_KEY != 'YOUR_OPENROUTER_KEY_HERE' else 'NOT SET'}")
    print(f"  Token Factory key: {'set' if TOKEN_FACTORY_API_KEY != 'YOUR_TOKEN_FACTORY_KEY_HERE' else 'NOT SET'}")
    raw    = call_llm('Reply with exactly: {"status": "ok", "thought": "connection works"}')
    result = parse_llm_json(raw)
    if result.get("status") == "ok":
        print("  LLM connection OK")
        return True
    else:
        print(f"  Unexpected response: {result}")
        return False
