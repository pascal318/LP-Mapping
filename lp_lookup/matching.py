from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from rapidfuzz import fuzz, process

from .config import FUZZY_SCORE_FLOOR, FUZZY_SCORE_MARGIN
from .models import InvestorMatch

GENERIC_TOKENS = {
    "advisors",
    "advisor",
    "asset",
    "assets",
    "associates",
    "bank",
    "banks",
    "capital",
    "co",
    "collective",
    "companies",
    "company",
    "corporate",
    "equity",
    "finance",
    "financial",
    "fund",
    "funds",
    "global",
    "group",
    "growth",
    "holding",
    "holdings",
    "industry",
    "international",
    "invest",
    "investment",
    "investments",
    "investisseur",
    "investissement",
    "investor",
    "investors",
    "management",
    "of",
    "partner",
    "partners",
    "private",
    "public",
    "strategic",
    "street",
    "technologies",
    "technology",
    "the",
    "venture",
    "ventures",
    "vision",
    "and",
}
GENERIC_SUFFIXES = tuple(sorted(GENERIC_TOKENS, key=len, reverse=True))


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower().strip()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"\(.*?\)", " ", normalized)
    normalized = normalized.replace("'", "").replace("’", "")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def core_tokens(value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for token in normalize_name(value).split():
        if token in GENERIC_TOKENS:
            continue

        stripped = token
        for suffix in GENERIC_SUFFIXES:
            if stripped.endswith(suffix) and len(stripped) > len(suffix) + 2:
                stripped = stripped[: -len(suffix)]
                break

        if stripped and stripped not in GENERIC_TOKENS and len(stripped) >= 2:
            tokens.append(stripped)
    return tuple(tokens)


def structurally_compatible(left: str, right: str) -> bool:
    left_tokens = core_tokens(left)
    right_tokens = core_tokens(right)
    if not left_tokens or not right_tokens:
        return False

    if left_tokens == right_tokens:
        return True

    overlap = set(left_tokens) & set(right_tokens)
    if len(overlap) >= 2:
        return True

    if len(overlap) != 1:
        return False

    token = next(iter(overlap))
    return (
        len(token) >= 4
        and left_tokens[0] == token
        and right_tokens[0] == token
        and (len(left_tokens) == 1 or len(right_tokens) == 1)
    )


@dataclass(frozen=True)
class MatchResult:
    matches: tuple[InvestorMatch, ...]
    best_candidate: str | None
    best_score: int | None


class InvestorMatcher:
    def __init__(
        self,
        fund_managers: Iterable[str],
        fuzzy_score_floor: int = FUZZY_SCORE_FLOOR,
        fuzzy_score_margin: int = FUZZY_SCORE_MARGIN,
    ) -> None:
        self.fund_managers = tuple(sorted({manager.strip() for manager in fund_managers if manager and manager.strip()}))
        self.fuzzy_score_floor = fuzzy_score_floor
        self.fuzzy_score_margin = fuzzy_score_margin

        self._exact = {manager: manager for manager in self.fund_managers}
        self._normalized_to_managers: dict[str, list[str]] = defaultdict(list)
        for manager in self.fund_managers:
            self._normalized_to_managers[normalize_name(manager)].append(manager)
        self._normalized_choices = tuple(sorted(key for key in self._normalized_to_managers if key))

    def match(self, company: str, raw_investor: str) -> MatchResult:
        investor = raw_investor.strip()
        if investor in self._exact:
            return MatchResult(
                matches=(
                    InvestorMatch(
                        company=company,
                        raw_investor=investor,
                        matched_fund_manager=investor,
                        match_method="exact",
                        match_score=100,
                    ),
                ),
                best_candidate=investor,
                best_score=100,
            )

        normalized_investor = normalize_name(investor)
        if normalized_investor and normalized_investor in self._normalized_to_managers:
            matches = tuple(
                InvestorMatch(
                    company=company,
                    raw_investor=investor,
                    matched_fund_manager=manager,
                    match_method="normalized",
                    match_score=100,
                )
                for manager in self._normalized_to_managers[normalized_investor]
            )
            return MatchResult(
                matches=matches,
                best_candidate=matches[0].matched_fund_manager if matches else None,
                best_score=100 if matches else None,
            )

        if not normalized_investor or not self._normalized_choices:
            return MatchResult(matches=(), best_candidate=None, best_score=None)

        scored_choices = process.extract(
            normalized_investor,
            self._normalized_choices,
            scorer=fuzz.WRatio,
            score_cutoff=self.fuzzy_score_floor,
            limit=10,
        )
        if not scored_choices:
            best_choice = process.extractOne(
                normalized_investor,
                self._normalized_choices,
                scorer=fuzz.WRatio,
            )
            if not best_choice:
                return MatchResult(matches=(), best_candidate=None, best_score=None)
            return MatchResult(
                matches=(),
                best_candidate=self._normalized_to_managers[best_choice[0]][0],
                best_score=int(round(best_choice[1])),
            )

        best_score = int(round(scored_choices[0][1]))
        accepted_choices = [
            choice
            for choice, score, _index in scored_choices
            if int(round(score)) >= self.fuzzy_score_floor
            and int(round(score)) >= best_score - self.fuzzy_score_margin
        ]

        matches: list[InvestorMatch] = []
        for choice in accepted_choices:
            score = int(round(next(score for candidate, score, _index in scored_choices if candidate == choice)))
            for manager in self._normalized_to_managers[choice]:
                if not structurally_compatible(investor, manager):
                    continue
                matches.append(
                    InvestorMatch(
                        company=company,
                        raw_investor=investor,
                        matched_fund_manager=manager,
                        match_method="fuzzy",
                        match_score=score,
                    )
                )

        matches.sort(key=lambda item: (-item.match_score, item.matched_fund_manager))
        best_candidate = self._normalized_to_managers[scored_choices[0][0]][0]
        return MatchResult(
            matches=tuple(matches),
            best_candidate=matches[0].matched_fund_manager if matches else best_candidate,
            best_score=best_score,
        )
