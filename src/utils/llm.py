"""Single entry point for LLM calls, backed by LiteLLM.

LiteLLM speaks one request/response format to every provider, so moving between
a hosted model and a local one is just a change of model name:

    ask("Summarize these alerts", model="gemini/gemini-flash-latest")
    ask("Summarize these alerts", model="ollama/llama3.1")

Credentials come from the environment, the same way ``notifications/`` reads its
Gmail settings:
  - ``GEMINI_API_KEY``:  required by the ``gemini/*`` models
  - ``LLM_MODEL``:       optional, overrides DEFAULT_MODEL
  - ``OLLAMA_API_BASE``: optional, defaults to http://localhost:11434

Local Ollama models need no key: the server just has to be running.
"""

import os

from litellm import completion

try:
    # Locally, load the variables from a .env file if there is one.
    # On GitHub Actions there is no .env and the variables come from the
    # secrets, so if python-dotenv is not installed this is simply ignored.
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_MODEL = "gemini/gemini-flash-latest"


def ask(
    prompt: str,
    model: str | None = None,
    system: str | None = None,
    temperature: float = 0.2,
) -> str:
    """Sends a single prompt to the model and returns its answer as plain text.

    ``model`` defaults to the LLM_MODEL environment variable, and to
    DEFAULT_MODEL when that is not set either. ``system`` is an optional
    instruction that frames how the model should answer.
    """
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = completion(
        model=model or os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""
