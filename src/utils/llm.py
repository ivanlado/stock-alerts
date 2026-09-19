"""Single entry point for LLM calls, backed by LiteLLM.

LiteLLM speaks one request/response format to every provider, so moving between
a hosted model and a local one is just a change of model name:

    ask("Summarize these alerts", model="gemini/gemini-flash-latest")
    ask("Summarize these alerts", model="ollama/llama3.1")

Credentials come from the environment, the same way ``notifications/`` reads its
Gmail settings:
  - ``GEMINI_API_KEY``:   required by the ``gemini/*`` models
  - ``LLM_MODEL``:        optional, overrides DEFAULT_MODEL
  - ``LLM_MIN_INTERVAL``: optional, seconds between calls (see below)
  - ``OLLAMA_API_BASE``:  optional, defaults to http://localhost:11434

Local Ollama models need no key: the server just has to be running.

CALLS ARE THROTTLED, AND WHY. The free tier of ``gemini-3.8-flash`` allows
5 requests a minute and 20 a day (measured on 2026-09-19 from the quota errors
themselves; other models and paid keys differ). Firing calls as fast as the
network allows means everything after the fifth comes back 429 -- which,
because a failed call leaves an empty cell, quietly turns into a dashboard with
no text on it and nothing visibly broken. So calls are spaced out here, in the
one place every one of them goes through. A cold run is slower; it is also the
difference between a full page and an empty one.

TWO 429s THAT LOOK ALIKE AND ARE NOT. The free tier limits requests per minute
AND per day, and both come back as a quota error -- not even reliably the same
exception class. The per-minute one is worth waiting out: it says how long, and
half a minute later the call works. The daily one is not: nothing will work
until the quota resets, and retrying it only makes the run take an hour to
produce the same nothing. They are told apart by the quota the message names,
and by whether the API offered a retry delay, which only the per-minute one
does.

And once the daily quota is gone, it is gone for every call that follows. So
the first one to hit it trips a switch and the rest of the run fails instantly
instead of spending three seconds each to be told the same thing a hundred
times over. The switch lives for the process, which is one run.
"""

import os
import re
import threading
import time

from litellm import completion
from litellm.exceptions import RateLimitError

try:
    # Locally, load the variables from a .env file if there is one.
    # On GitHub Actions there is no .env and the variables come from the
    # secrets, so if python-dotenv is not installed this is simply ignored.
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_MODEL = "gemini/gemini-flash-latest"

# Seconds between two calls. 12.5s is a shade over the free tier's ceiling of
# 5 requests a minute, with room for the clocks to disagree. Set it to 0 for a
# local model, where nothing is being rationed.
MIN_INTERVAL = float(os.environ.get("LLM_MIN_INTERVAL", "12.5"))

# How many times a call that is rate-limited anyway is waited out and retried.
RATE_LIMIT_RETRIES = 3

# The longest a single rate-limited call is allowed to park the run.
MAX_RETRY_WAIT = 65.0

# What the daily quota error says, whichever exception class it arrives as.
_DAILY_QUOTA_MARKERS = ("PerDay", "per day")

# The throttle's state. A lock rather than a bare timestamp so that the day
# this is called from several threads, the spacing still holds.
_lock = threading.Lock()
_last_call = 0.0

# Tripped by the first daily-quota error; see the module docstring.
_daily_quota_spent = False


class DailyQuotaExhausted(RuntimeError):
    """Raised once the model's daily allowance is gone, and for every call
    after that, without asking again."""


def _is_daily_quota(error: Exception) -> bool:
    message = str(error)
    return any(marker in message for marker in _DAILY_QUOTA_MARKERS)


def _wait_turn() -> None:
    """Blocks until enough time has passed since the previous call."""
    global _last_call
    with _lock:
        pending = MIN_INTERVAL - (time.monotonic() - _last_call)
        if pending > 0:
            time.sleep(pending)
        _last_call = time.monotonic()


def _retry_after(error: Exception) -> float | None:
    """The wait the API asked for in seconds, or None when it offered none.

    Gemini puts it in the error message as "Please retry in 26.66s", which is
    the only place LiteLLM surfaces it for this provider. Its absence is what
    marks a limit that waiting cannot fix, such as the daily quota.
    """
    match = re.search(r"retry in ([0-9.]+)s", str(error))
    if not match:
        return None
    # A second of margin: the server's clock and ours are not the same, and
    # the cap keeps a wild number from parking the run for an hour.
    return min(float(match.group(1)) + 1.0, MAX_RETRY_WAIT)


def ask(
    prompt: str,
    model: str | None = None,
    system: str | None = None,
    temperature: float = 0.2,
    web_search: bool = False,
    num_retries: int = 2,
) -> str:
    """Sends a single prompt to the model and returns its answer as plain text.

    ``model`` defaults to the LLM_MODEL environment variable, and to
    DEFAULT_MODEL when that is not set either. ``system`` is an optional
    instruction that frames how the model should answer.

    ``web_search`` lets the model ground its answer in Google Search, which is
    the only way to ask about anything more recent than its training data. It
    only works on the ``gemini/*`` models, and on the free tier it has its own
    small daily quota, separate from the ordinary one: once that runs out the
    call fails with a 429 while plain calls keep working.

    Calls are spaced out (see the module docstring). A call stopped by the
    per-minute limit is waited out and retried; the daily quota raises
    ``DailyQuotaExhausted`` straight away, and so does every call after it.
    Either way the caller decides what an unanswered question means.
    """
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    global _daily_quota_spent
    if _daily_quota_spent:
        raise DailyQuotaExhausted("The model's daily quota is spent; not asking again")

    for attempt in range(RATE_LIMIT_RETRIES + 1):
        _wait_turn()
        try:
            response = completion(
                model=model or os.environ.get("LLM_MODEL", DEFAULT_MODEL),
                messages=messages,
                temperature=temperature,
                tools=[{"googleSearch": {}}] if web_search else None,
                num_retries=num_retries,
            )
            return response.choices[0].message.content or ""
        except Exception as error:
            if _is_daily_quota(error):
                _daily_quota_spent = True
                print("The model's daily quota is spent; skipping the rest of the run")
                raise
            if not isinstance(error, RateLimitError):
                raise
            wait = _retry_after(error)
            if wait is None or attempt == RATE_LIMIT_RETRIES:
                # A minute-long limit already waited out as long as it is
                # worth, or one that did not say how long to wait.
                raise
            print(f"Rate limited, waiting {wait:.0f}s before retrying")
            time.sleep(wait)

    # Unreachable: the loop either returns or raises.
    return ""
