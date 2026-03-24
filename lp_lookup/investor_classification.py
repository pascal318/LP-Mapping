from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ENTITY_KEEP = {
    "Alibaba Cloud",
    "Allied Minds",
    "Analog Devices",
    "Apollo Projects",
    "Beyond Net Zero",
    "Bloomberg Beta",
    "Blue Moon",
    "Blue Owl",
    "Bpifrance",
    "Charles Schwab",
    "Chipotle Mexican Grill",
    "Deutsche Telekom",
    "Driving Forces",
    "Future Fifty",
    "La Famiglia",
    "Marshall Wace",
    "Mayo Clinic",
    "Societe Generale",
    "T. Rowe Price",
    "Tishman Speyer",
    "United States Air Force",
    "United States Space Force",
    "Work-Bench",
}

PERSON_FORCE = {
    "DJ Patil",
    "JAY-Z Shawn Carter",
    "JB Straubel",
    "Jr.",
    "Mei Z.",
}

ENTITY_TERMS = {
    "accelerator",
    "advisors",
    "advisor",
    "aerospace",
    "airlines",
    "airways",
    "alliance",
    "alternatives",
    "angel",
    "angels",
    "association",
    "associates",
    "authority",
    "bank",
    "banks",
    "beta",
    "biotech",
    "biosciences",
    "capital",
    "clinic",
    "cloud",
    "club",
    "collective",
    "college",
    "commission",
    "companies",
    "company",
    "corporation",
    "corporate",
    "credit",
    "development",
    "devices",
    "electric",
    "electronics",
    "energy",
    "enterprise",
    "enterprises",
    "equity",
    "family office",
    "finance",
    "financial",
    "foundation",
    "fund",
    "funds",
    "government",
    "group",
    "grill",
    "health",
    "healthcare",
    "holding",
    "holdings",
    "hospital",
    "hospitals",
    "inc",
    "institute",
    "institutes",
    "insurance",
    "invest",
    "investment",
    "investments",
    "investor",
    "investors",
    "labs",
    "lab",
    "limited",
    "llc",
    "ltd",
    "management",
    "market",
    "markets",
    "media",
    "motors",
    "network",
    "networks",
    "office",
    "partner",
    "partners",
    "pension",
    "pharma",
    "platform",
    "platforms",
    "power",
    "projects",
    "properties",
    "property",
    "realty",
    "research",
    "robotics",
    "school",
    "securities",
    "spark",
    "strategic",
    "studio",
    "studios",
    "super",
    "syndicate",
    "system",
    "systems",
    "tech",
    "technology",
    "telecom",
    "telecommunications",
    "therapeutics",
    "university",
    "venture",
    "ventures",
}

ENTITY_PATTERNS = (
    r"\b[A-Z]{2,}\b",
    r"\d",
    r"&",
    r"/",
)

PERSON_PARTICLES = {"al", "bin", "da", "de", "del", "der", "di", "du", "la", "le", "van", "von"}


@lru_cache(maxsize=1)
def _load_propernames() -> frozenset[str]:
    path = Path("/usr/share/dict/propernames")
    if not path.exists():
        return frozenset()
    with path.open(encoding="utf-8", errors="ignore") as handle:
        return frozenset(line.strip() for line in handle if line.strip())


def _normalize_words(value: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", value.lower()).strip() + " "


def _has_entity_term(value: str) -> bool:
    normalized = _normalize_words(value)
    return any(f" {term} " in normalized for term in ENTITY_TERMS)


def _tokenise(value: str) -> list[str]:
    cleaned = value.replace("’", "'").replace(".", " ")
    return [token for token in re.split(r"[\s\-]+", cleaned) if token]


def is_likely_individual_investor(value: str) -> bool:
    if value in ENTITY_KEEP:
        return False
    if value in PERSON_FORCE:
        return True
    if _has_entity_term(value):
        return False
    if any(re.search(pattern, value) for pattern in ENTITY_PATTERNS):
        return False

    tokens = _tokenise(value)
    if len(tokens) < 2 or len(tokens) > 4:
        return False
    if any(not re.search(r"[A-Za-z]", token) for token in tokens):
        return False
    if any(not token[0].isupper() for token in tokens if token.lower() not in PERSON_PARTICLES):
        return False

    propernames = _load_propernames()
    first = tokens[0].strip("'")
    has_name_signal = first in propernames or len(first) <= 2 or any(len(token) == 1 for token in tokens)
    if has_name_signal:
        return True

    return len(tokens) in (2, 3) and all(token.lower() not in PERSON_PARTICLES for token in tokens)
