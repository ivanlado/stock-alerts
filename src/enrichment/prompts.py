"""The prompts asked about each alerted company.

THIS FILE IS THE ONE TO EDIT to change what the model is asked. Everything else
in ``enrichment/`` is plumbing that does not care what the questions say.

A template is an ordinary string with ``{placeholders}`` in it. Any column of
the alert DataFrame can be used as a placeholder -- ``{ticker}``, ``{current}``,
``{var_1m}``... -- plus ``{name}`` for the company's display name. Placeholders
that a template does not mention are simply ignored. Numbers arrive already
rounded, and percentage columns (``var_*``, ``pct_*``) already carry their own
``%`` sign, so no format specifiers and no trailing ``%`` are needed here.

The answers are the only text in this repository that is NOT in English: they
are what the reader of the dashboard reads, and the reader asked for Spanish.
Everything around them -- names, comments, headings -- stays English as usual.

TWO KINDS OF QUESTION, AND WHY THEY ARE SEPARATED.

``PROFILE`` asks what a company IS: what it sells, what protects it, who it
competes with. That barely moves from one day to the next, so the answer is
cached on disk by ``profiles.py`` and re-asked only every few months.
``ANALYST_DIVERGENCE`` and ``PRICE_DROP`` ask why TODAY's number looks the way
it does, which is worthless if it is a month old, so they are asked on every
run.

WHY THE PROFILE IS ONE QUESTION AND NOT SIX. Gemini's free tier allows twenty
requests A DAY. Six questions per company would mean three companies a day and
a dashboard that takes a week to fill in; one question that answers all six
sections at once means the whole shortlist fits in a single run. The model is
asked for JSON so the six answers can be told apart again.
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
    "Eres un analista financiero que escribe un informe breve para un inversor "
    "particular. Responde SIEMPRE en castellano, de forma concisa, concreta y "
    "factual, en texto plano y sin titulares ni viñetas. Si no sabes algo, dilo "
    "claramente en lugar de inventarlo: un motivo equivocado es peor que "
    "ninguno."
)


# --- The stable profile: asked once per company and cached for months ---

# The keys of the JSON the model is asked for, each with the question it
# answers. They are also the keys the web reads inside `profile`, so adding one
# here and rendering it in CompanyCards.tsx is all it takes.
PROFILE_SECTIONS: dict[str, str] = {
    "summary": (
        "a qué se dedica la empresa, en dos frases como máximo y sin adjetivos "
        "de marketing"
    ),
    "revenue_sources": (
        "sus principales fuentes de ingresos: las tres o cuatro mayores, con el "
        "peso aproximado sobre el total si lo conoces"
    ),
    "moat": (
        "su foso económico: de qué tipo es (escala, marca, costes de cambio, "
        "red, patentes) y cómo de sólido parece, o si no lo tiene"
    ),
    "competitors": (
        "sus principales competidores, con su ticker cuando coticen"
    ),
    "threats": (
        "sus principales amenazas: regulatorias, competitivas, tecnológicas o "
        "financieras, las que de verdad apliquen"
    ),
    "outlook": (
        "qué se espera de su futuro: crecimiento esperado del negocio y los "
        "riesgos que podrían impedirlo, dejando claro que es una expectativa"
    ),
}


def _profile_template() -> str:
    """The profile question, built from the sections above.

    Written as a function so the list of sections stays the single source of
    truth: adding one to ``PROFILE_SECTIONS`` changes the question too.
    """
    fields = ",\n".join(
        f'  "{key}": "{description}"' for key, description in PROFILE_SECTIONS.items()
    )
    return (
        "Describe {name} ({ticker}) para un inversor particular.\n\n"
        "Responde ÚNICAMENTE con un objeto JSON, sin texto alrededor y sin "
        "marcas de código, con exactamente estas claves, cuyo valor es una "
        "cadena de texto en castellano que responde a lo que describe la "
        "plantilla:\n"
        "{{\n" + fields + "\n}}\n\n"
        "Cada valor, tres frases como máximo. Si no sabes lo que pide una "
        "clave, deja su valor como cadena vacía en lugar de inventarlo."
    )


PROFILE = Prompt(template=_profile_template())


# --- The volatile commentary: asked on every run, about today's numbers ---

# Asked for the rows of analyst_alerts.
ANALYST_DIVERGENCE = Prompt(
    template=(
        "{name} ({ticker}) cotiza a {current} y el precio objetivo mediano de "
        "los analistas es {median}, un {pct_price_diff} de diferencia. "
        "En cuatro frases como máximo: ¿por qué valoran los analistas la "
        "empresa de forma tan distinta al mercado?"
    ),
    web_search=True,
)


# Asked for the rows of price_alerts.
PRICE_DROP = Prompt(
    template=(
        "{name} ({ticker}) se ha movido un {var_1m} en el último mes, "
        "{var_3m} en tres meses, {var_6m} en seis meses y {var_9m} en nueve "
        "meses. En cuatro frases como máximo: ¿qué explica ese movimiento "
        "reciente de la cotización?"
    ),
    web_search=True,
)
