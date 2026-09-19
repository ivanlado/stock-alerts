"""The stable half of the LLM commentary, cached on disk.

WHAT A PROFILE IS. Six answers about a company -- what it does, where its
revenue comes from, its moat, its competitors, its threats and what is expected
of it -- written by the model in ONE call and kept as one JSON file per ticker.
One call, not six, because the free tier allows twenty a day: see ``prompts``.

WHY IT IS CACHED AND THE REST IS NOT. None of those six answers changes between
a Tuesday and a Wednesday: a company's competitors are the same today as they
were last month. Asking them again on every daily run would cost six calls per
alerted company for an answer that is already on disk. What DOES change daily --
why the price moved, why analysts disagree with the market -- stays in
``commentary.py`` and is asked every time, because a stale answer there is a
wrong answer.

So a profile is rewritten only when it is missing, when it is older than
``TTL_DAYS``, or when a new section has been added to ``prompts.py`` and the
stored file does not have it yet.

WHERE IT LIVES. Next to the Parquet archive, under ``HISTORY_DIR``. That is the
directory CI checks out from the ``data`` branch and commits at the end of the
run, so the cache survives from one GitHub Actions run to the next, where
anything written into the code checkout would be thrown away.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from enrichment import prompts
from utils.llm import ask

REPO_ROOT = Path(__file__).resolve().parents[2]

# Same variable ``export/history_export.py`` reads, for the same reason: CI
# points it at the checked-out ``data`` branch. Locally it falls back to
# ``history/`` at the repo root, which is gitignored but persists on disk.
HISTORY_DIR = Path(os.environ.get("HISTORY_DIR") or REPO_ROOT / "history")
PROFILES_DIR = Path(os.environ.get("PROFILES_DIR") or HISTORY_DIR / "profiles")

# How long an answer is trusted before it is asked again. Long on purpose: the
# facts these questions ask about move over quarters, not days.
TTL_DAYS = 90


def _path(ticker: str) -> Path:
    """One file per ticker, so two runs never fight over the same file."""
    # Tickers like ``BRK-B`` are already filename-safe; a dot (``BMW.DE``) is
    # replaced so it does not read as a second extension.
    return PROFILES_DIR / f"{ticker.replace('.', '_')}.json"


def _load(ticker: str) -> dict:
    """The stored profile, or an empty one when there is nothing usable."""
    path = _path(ticker)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        # A corrupted cache entry is not worth a crash: regenerate it.
        print(f"Profile cache unreadable for {ticker}: {exc}")
        return {}


def _is_fresh(stored: dict) -> bool:
    generated_at = stored.get("generated_at")
    if not generated_at:
        return False
    try:
        written = datetime.fromisoformat(generated_at)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - written < timedelta(days=TTL_DAYS)


def _save(ticker: str, profile: dict) -> None:
    path = _path(ticker)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        # The run does not depend on the cache being written: worst case the
        # next run asks again.
        print(f"Could not write the profile of {ticker}: {exc}")


def _extract_json(answer: str) -> dict:
    """The JSON object inside the model's answer, or an empty dict.

    Models fence their JSON in ``` blocks, or introduce it with a sentence,
    however firmly they are asked not to. Taking the outermost braces copes
    with both without a second call.
    """
    start = answer.find("{")
    end = answer.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(answer[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _ask_profile(name: str, ticker: str) -> dict[str, str | None]:
    """The six sections in one call. Empty when the call or the parsing fails.

    An empty string is treated as no answer: the prompt asks for one where the
    model does not know, and a blank section should read as missing rather than
    as an answer that happens to say nothing.
    """
    try:
        answer = ask(
            prompts.PROFILE.render(name=name, ticker=ticker),
            system=prompts.SYSTEM,
            web_search=prompts.PROFILE.web_search,
        )
    except Exception as exc:
        print(f"LLM call failed ({type(exc).__name__}): {exc}")
        return {}

    parsed = _extract_json(answer)
    if not parsed:
        print(f"Could not read a profile out of the answer for {ticker}")
        return {}

    sections: dict[str, str | None] = {}
    for key in prompts.PROFILE_SECTIONS:
        value = parsed.get(key)
        sections[key] = value.strip() if isinstance(value, str) and value.strip() else None
    return sections


def get_profile(ticker: str, name: str) -> dict:
    """The profile of one company, from the cache when it is still good.

    Returns ``{"generated_at": ..., "sections": {key: text | None}}``. A
    section the model could not answer is None rather than missing, so the web
    can simply skip it.
    """
    stored = _load(ticker)
    sections: dict[str, str | None] = dict(stored.get("sections") or {})
    fresh = _is_fresh(stored)

    # Nothing to do when the stored answer is recent and complete. A section
    # added to prompts.py after it was written counts as incomplete.
    if fresh and all(sections.get(key) for key in prompts.PROFILE_SECTIONS):
        return stored

    print(f"Profile for {ticker}: asking the model")
    answered = _ask_profile(name, ticker)
    if not any(answered.values()):
        # The call failed, or came back unreadable. Keeping whatever was
        # already on disk beats storing six nulls and calling them fresh.
        return stored

    # Whatever the model did not answer this time keeps its previous text, if
    # there was any. Keys no longer in prompts.py are dropped, so removing a
    # question also removes it from the web.
    sections = {key: answered.get(key) or sections.get(key) for key in prompts.PROFILE_SECTIONS}

    profile = {
        "ticker": ticker,
        "name": name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": os.environ.get("LLM_MODEL", "default"),
        "sections": sections,
    }
    _save(ticker, profile)
    return profile


def get_profiles(companies: dict[str, str]) -> dict[str, dict]:
    """``{ticker: display name}`` -> ``{ticker: profile}``."""
    return {ticker: get_profile(ticker, name) for ticker, name in companies.items()}
