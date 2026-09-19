"""The prompts asked about each alerted company.

THIS FILE IS THE ONE TO EDIT to change what the model is asked. Everything else
in ``enrichment/`` is plumbing that does not care what the questions say.

A template is an ordinary string with ``{placeholders}`` in it. Any column of
the alert DataFrame can be used as a placeholder -- ``{ticker}``, ``{current}``,
``{var_1m}``... -- plus ``{name}`` for the company's display name. Placeholders
that a template does not mention are simply ignored. Numbers arrive already
rounded, and percentage columns (``var_*``, ``pct_*``) already carry their own
``%`` sign, so no format specifiers and no trailing ``%`` are needed here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Prompt:
    """A question template plus how it has to be run.

    ``web_search`` grounds the answer in Google Search. Turn it on for anything
    the model cannot know from training alone -- recent news, this week's price
    move -- and leave it off for stable facts, because it is billed against a
    separate and much smaller free-tier quota.
    """

    template: str
    web_search: bool = False

    def render(self, **values: str) -> str:
        return self.template.format(**values)


# Framing applied to every question below.
SYSTEM = (
    "You are a financial analyst writing a short briefing for a retail "
    "investor. Be concise, concrete and factual. If you do not know something, "
    "say so plainly instead of guessing: a wrong reason is worse than no reason."
)


# Asked once per company, for both kinds of alert.
BUSINESS = Prompt(
    template=(
        "In no more than three sentences: what does {name} ({ticker}) do, and "
        "where does the majority of its revenue come from?"
    ),
)


# Asked for the rows of analyst_alerts.
ANALYST_DIVERGENCE = Prompt(
    template=(
        "{name} ({ticker}) trades at {current}, while the analysts' median "
        "price target is {median}, which is {pct_price_diff} away. "
        "In no more than four sentences: why do analysts value the company so "
        "differently from the market?"
    ),
    web_search=True,
)


# Asked for the rows of price_alerts.
PRICE_DROP = Prompt(
    template=(
        "{name} ({ticker}) has moved {var_1m} over the last month, "
        "{var_3m} over three months, {var_6m} over six months and "
        "{var_9m} over nine months. "
        "In no more than four sentences: what explains the drop?"
    ),
    web_search=True,
)
