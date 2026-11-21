"""Text normalisation, synonyms, fuzzy matching and intent vocabulary."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

STOPWORDS = {
    "a",
    "an",
    "the",
    "of",
    "for",
    "in",
    "on",
    "at",
    "to",
    "and",
    "or",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "with",
    "from",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "me",
    "my",
    "our",
    "we",
    "us",
    "i",
    "you",
    "your",
    "please",
    "show",
    "tell",
    "give",
    "calculate",
    "compute",
    "find",
    "get",
    "what",
    "whats",
    "how",
    "which",
    "who",
    "where",
    "do",
    "does",
    "did",
    "can",
    "could",
    "would",
    "there",
    "any",
    "about",
    "overall",
    "currently",
    "just",
    "all",
    "each",
    "per",
    "by",
}

GROUP_TRIGGERS = {
    "by",
    "per",
    "across",
    "compare",
    "comparison",
    "breakdown",
    "split",
    "group",
    "grouped",
    "each",
    "for each",
    "divided",
}

RANK_TOKENS = {
    "top",
    "bottom",
    "highest",
    "lowest",
    "best",
    "worst",
    "most",
    "least",
    "largest",
    "smallest",
    "leading",
    "rank",
    "ranked",
    "ranking",
    "greatest",
    "maximum",
    "minimum",
}

TIME_TOKENS = {
    "trend",
    "trends",
    "over time",
    "timeline",
    "monthly",
    "weekly",
    "daily",
    "yearly",
    "annual",
    "quarterly",
    "by month",
    "per month",
    "by year",
    "by week",
    "by day",
    "progression",
    "seasonality",
}

OUTLIER_TOKENS = {"outlier", "outliers", "unusual", "anomaly", "anomalies", "abnormal", "extreme"}

MISSING_TOKENS = {"missing", "null", "nulls", "empty", "blank", "incomplete", "nan"}

OVERVIEW_TOKENS = {
    "summarize",
    "summarise",
    "summary",
    "overview",
    "describe this data",
    "describe the data",
    "explain this data",
    "what is this data",
    "dataset overview",
    "dataset summary",
    "about this dataset",
}

CORRELATION_TOKENS = {"correlation", "correlated", "relationship", "related", "association"}

SCHEMA_TOKENS = {"schema", "columns", "fields", "attributes", "column names", "what columns"}

DISTRIBUTION_TOKENS = {"distribution", "histogram", "spread", "percentile", "percentiles"}

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
}

# Concept vocabulary helps match "sales" to a revenue column, "qty" to units, etc.
CONCEPT_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": (
        "revenue",
        "sales",
        "turnover",
        "income",
        "earnings",
        "proceeds",
        "gross revenue",
        "total sales",
        "billing",
        "mrr",
        "arr",
        "revenue generated",
    ),
    "profit": ("profit", "profits", "net profit", "net income", "margin", "earnings", "bottom line"),
    "cost": ("cost", "costs", "expense", "expenses", "cogs", "overhead", "spending"),
    "price": ("price", "unit price", "rate", "cost per unit", "list price", "price per unit"),
    "quantity": ("quantity", "qty", "units", "units sold", "units purchased", "number of units", "seats", "volume"),
    "discount": ("discount", "discount percent", "markdown", "promo", "promotion"),
    "amount": ("amount", "transaction amount", "bill amount", "total bill", "value"),
    "salary": ("salary", "annual salary", "wage", "pay", "compensation", "payroll"),
    "score": ("score", "rating", "satisfaction score", "risk score", "usage score", "performance rating"),
    "days": ("days", "duration", "tenure", "delay days", "length of stay", "days on market"),
    "fee": ("fee", "fees", "freight cost", "shipping cost", "charges"),
    "spend": ("ad spend", "spend", "advertising spend", "budget"),
    "age": ("age", "patient age", "years old"),
    "roas": ("roas", "return on ad spend"),
    "conversion": ("conversion", "conversions", "conversion rate"),
}

COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "region": ("region", "regions", "area", "territory", "location", "geography", "market"),
    "category": ("category", "categories", "type", "segment", "class", "group"),
    "product": ("product", "products", "item", "sku", "product name"),
    "customer_segment": ("customer segment", "segment", "customer type", "audience"),
    "department": ("department", "departments", "division", "team"),
    "platform": ("platform", "platforms", "channel", "source"),
    "transport_mode": ("transport mode", "mode", "shipping mode", "carrier mode"),
    "city": ("city", "cities", "town", "metro", "location"),
    "plan_tier": ("plan tier", "plan", "tier", "subscription plan"),
    "merchant_category": ("merchant category", "merchant", "merchant type"),
    "property_type": ("property type", "home type", "house type"),
    "genre": ("genre", "genres", "category"),
    "device_type": ("device type", "device", "devices"),
    "ticker_symbol": ("ticker", "ticker symbol", "symbol", "asset"),
    "asset_name": ("asset name", "asset", "coin", "token"),
    "order_date": ("order date", "date", "order time"),
    "signup_date": ("signup date", "date", "signup"),
}

DATE_WORDS = {
    "date",
    "day",
    "week",
    "month",
    "year",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "yearly",
    "annual",
    "time",
    "timeline",
    "trend",
    "trends",
    "over time",
    "seasonality",
}

AGGREGATION_WORDS: dict[str, set[str]] = {
    "sum": {"total", "sum", "summed", "combined", "aggregate", "altogether"},
    "mean": {"average", "avg", "mean", "typical"},
    "median": {"median", "middle"},
    "min": {"minimum", "min", "lowest", "smallest", "least"},
    "max": {"maximum", "max", "highest", "greatest", "largest", "peak"},
    "std": {"standard deviation", "std", "stddev", "volatility", "dispersion"},
    "var": {"variance", "var"},
    "count": {"count", "number", "how many", "frequency", "frequent", "occurrences"},
    "nunique": {"unique", "distinct", "different"},
    "range": {"range", "spread"},
}

OFF_TOPIC = {
    "weather",
    "joke",
    "president",
    "capital of",
    "recipe",
    "song",
    "movie",
    "football",
    "cricket",
    "who won",
    "news",
    "sports",
    "politics",
    "write code",
    "python code",
    "sql injection",
    "ignore previous",
    "system prompt",
    "dinner",
}

GREETING_WORDS = {"hi", "hello", "hey", "hola", "yo", "howdy", "greetings", "sup"}
POLITE_WORDS = {"thanks", "thank", "thx", "awesome", "great", "cool", "perfect", "nice", "appreciate"}
FAREWELL_WORDS = {"bye", "goodbye", "cya", "farewell", "quit", "exit"}


@dataclass
class NormalizedQuestion:
    raw: str
    text: str
    tokens: list[str]
    token_set: set[str]


def normalize(text: str) -> str:
    s = str(text or "").lower().strip()
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"[’']", "", s)
    # Keep comparison operators and percent for filter parsing.
    s = re.sub(r"[^a-z0-9\s<>=%\.]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9%]+", normalize(text)) if t]


def singular(word: str) -> str:
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("es") and word[:-2].endswith(("s", "x", "ch", "sh")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def stem_set(tokens: list[str]) -> set[str]:
    return {singular(t) for t in tokens}


def fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def normalize_question(question: str) -> NormalizedQuestion:
    text = normalize(question)
    tokens = tokenize(question)
    return NormalizedQuestion(raw=str(question), text=text, tokens=tokens, token_set=set(tokens))


def contains_phrase(text: str, phrase: str) -> bool:
    phrase = normalize(phrase)
    if not phrase:
        return False
    if " " in phrase:
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def contains_any(text: str, words: set[str]) -> list[str]:
    return [w for w in words if contains_phrase(text, w)]


def extract_limit(text: str, default: int | None = None) -> int | None:
    m = re.search(r"\b(?:top|bottom|first|last|highest|lowest)\s+(\d{1,3})\b", text)
    if m:
        return max(1, min(int(m.group(1)), 1000))
    m = re.search(r"\b(\d{1,3})\s+(?:top|bottom|highest|lowest|best|worst)\b", text)
    if m:
        return max(1, min(int(m.group(1)), 1000))
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b(?:top|bottom|first|last)\s+{word}\b", text):
            return value
    m = re.search(r"\b(\d{1,3})\b", text)
    if m and any(w in text for w in ("top", "bottom", "rank", "highest", "lowest")):
        return max(1, min(int(m.group(1)), 1000))
    return default


def extract_frequency(text: str) -> str | None:
    if re.search(r"\b(daily|by day|per day|each day)\b", text):
        return "D"
    if re.search(r"\b(weekly|by week|per week|each week)\b", text):
        return "W"
    if re.search(r"\b(monthly|by month|per month|each month|month over month|mom)\b", text):
        return "M"
    if re.search(r"\b(quarterly|by quarter|per quarter|each quarter)\b", text):
        return "Q"
    if re.search(r"\b(yearly|annual|annually|by year|per year|each year|year over year|yoy)\b", text):
        return "Y"
    return None


def detect_aggregation(text: str) -> str | None:
    # Check more specific operations before the generic sum/min/max words.
    if contains_phrase(text, "standard deviation") or contains_phrase(text, "std"):
        return "std"
    if contains_phrase(text, "variance"):
        return "var"
    if contains_phrase(text, "median"):
        return "median"
    if contains_phrase(text, "unique") or contains_phrase(text, "distinct"):
        return "nunique"
    if contains_phrase(text, "range"):
        return "range"
    if any(contains_phrase(text, w) for w in ("average", "avg", "mean", "typical")):
        return "mean"
    if any(contains_phrase(text, w) for w in ("most frequently", "frequency", "occurrences", "number of", "how many")):
        return "count"
    if any(contains_phrase(text, w) for w in ("total", "sum", "combined", "aggregate", "how much")):
        return "sum"
    if any(contains_phrase(text, w) for w in ("minimum", "min", "lowest", "smallest")):
        return "min"
    if any(contains_phrase(text, w) for w in ("maximum", "max", "highest", "greatest", "largest", "peak")):
        return "max"
    if any(contains_phrase(text, w) for w in ("count", "how many")):
        return "count"
    return None


def detect_direction(text: str) -> str | None:
    if any(contains_phrase(text, w) for w in ("lowest", "bottom", "worst", "least", "smallest", "minimum", "min", "fewest", "underperform", "ascending")):
        return "asc"
    if any(contains_phrase(text, w) for w in ("highest", "top", "best", "most", "largest", "maximum", "max", "leading", "descending", "rank")):
        return "desc"
    return None


def concept_for_column(name: str) -> str | None:
    lname = normalize(name)
    tokens = set(tokenize(name))
    best: tuple[int, str] | None = None
    for concept, aliases in CONCEPT_ALIASES.items():
        score = 0
        for alias in aliases:
            if contains_phrase(lname, alias):
                score = max(score, 10 + len(alias.split()))
            alias_tokens = set(tokenize(alias))
            overlap = tokens.intersection(alias_tokens)
            if overlap:
                score = max(score, len(overlap) * 3)
        if score and (best is None or score > best[0]):
            best = (score, concept)
    return best[1] if best else None


def column_aliases(name: str, kind: str) -> list[str]:
    aliases = {normalize(name)}
    tokens = tokenize(name)
    if tokens:
        aliases.add(" ".join(tokens))
        aliases.add(" ".join(singular(t) for t in tokens))
        if len(tokens) > 1:
            prefix = " ".join(tokens[:-1])
            if prefix not in STOPWORDS and prefix not in _GENERIC_MATCH_TOKENS:
                aliases.add(prefix)
            if tokens[0] in {"is", "has", "was", "total", "avg", "average"}:
                suffix = " ".join(tokens[1:])
                if suffix not in STOPWORDS:
                    aliases.add(suffix)
    for known, extra in COLUMN_ALIASES.items():
        if known == normalize(name) or known in aliases:
            aliases.update(extra)
    # Name-token aliases without the trailing "id".
    if tokens and tokens[-1] in {"id", "no", "number"} and len(tokens) > 1:
        base = " ".join(tokens[:-1])
        if base not in STOPWORDS:
            aliases.add(base)
    concept = concept_for_column(name)
    if concept:
        aliases.update(CONCEPT_ALIASES.get(concept, ()))
    return [a for a in aliases if a and a not in STOPWORDS and len(a) > 1]


_GENERIC_MATCH_TOKENS = {
    "total", "value", "number", "rate", "unit", "per", "average", "data",
    "record", "item", "count", "monthly", "weekly", "daily", "yearly",
    "annual", "quarterly",
}


def column_match_score(question_text: str, column: str, kind: str) -> float:
    """Score how strongly a question refers to a column (0-100)."""
    q = question_text
    aliases = column_aliases(column, kind)
    score = 0.0
    for alias in aliases:
        if not alias or alias in STOPWORDS or alias in _GENERIC_MATCH_TOKENS:
            continue
        if contains_phrase(q, alias):
            # Exact, longer phrases are stronger. Exact column names dominate.
            score = max(score, 60 + min(len(alias.split()), 4) * 8)
        else:
            alias_tokens = [t for t in tokenize(alias) if t not in STOPWORDS and t not in _GENERIC_MATCH_TOKENS]
            q_tokens = [t for t in tokenize(q) if t not in STOPWORDS]
            for at in alias_tokens:
                for qt in q_tokens:
                    if at == qt or singular(at) == singular(qt):
                        score = max(score, 34 if len(at) > 2 else 22)
                    elif len(at) >= 5 and fuzzy_ratio(at, qt) >= 0.86:
                        score = max(score, 20)
    lname = normalize(column)
    if lname and lname in q:
        score = max(score, 92)
    return min(score, 100.0)


def humanize(name: str) -> str:
    return str(name).replace("_", " ").strip().title()


def format_value(value: float, column: str | None = None, currency: bool | None = None) -> str:
    """Format a number for display. Currency detection is name-based only."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if currency is None:
        currency = is_currency_column(column or "")
    if currency:
        sign = "-" if value < 0 else ""
        abs_value = abs(value)
        return f"{sign}${abs_value:,.2f}" if abs_value < 1000 else f"{sign}${abs_value:,.0f}"
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"


_CURRENCY_TOKENS = {
    "revenue",
    "profit",
    "cost",
    "price",
    "bill",
    "salary",
    "spend",
    "mrr",
    "arr",
    "amount",
    "fee",
    "freight",
    "sale",
    "sales",
    "value",
    "income",
    "budget",
    "wage",
}


def is_currency_column(column: str) -> bool:
    # Match whole tokens so "square_feet" is not treated as a monetary "fee".
    tokens = {singular(t) for t in tokenize(column)}
    return any(singular(k) in tokens for k in _CURRENCY_TOKENS)


def is_percent_column(column: str) -> bool:
    name = normalize(column)
    return any(k in name for k in ("percent", "rate", "margin", "ratio", "discount", "roas", "return"))
