from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class LPFundPair:
    fund_manager: str
    lp_name: str
    lp_type: str
    city: str
    country: str


@dataclass(frozen=True)
class LPRecord:
    lp_name: str
    lp_type: str
    city: str
    country: str


@dataclass(frozen=True)
class CompanyInvestor:
    company: str
    raw_investor: str


@dataclass(frozen=True)
class InvestorMatch:
    company: str
    raw_investor: str
    matched_fund_manager: str
    match_method: str
    match_score: int


@dataclass(frozen=True)
class CompanyExposureRow:
    company: str
    lp_name: str
    matched_investors: tuple[str, ...]
    best_score: int
    lp_type: str
    city: str
    country: str


@dataclass(frozen=True)
class UnmatchedInvestor:
    company: str
    raw_investor: str
    best_candidate: Optional[str]
    best_score: Optional[int]


@dataclass(frozen=True)
class IndividualInvestor:
    company: str
    raw_investor: str


class SourceAdapter(ABC):
    @abstractmethod
    def load_lp_fund_pairs(self) -> Iterable[LPFundPair]:
        raise NotImplementedError

    @abstractmethod
    def load_unique_lps(self) -> Iterable[LPRecord]:
        raise NotImplementedError

    @abstractmethod
    def load_company_investors(self) -> Iterable[CompanyInvestor]:
        raise NotImplementedError

    @property
    @abstractmethod
    def source_paths(self) -> tuple[Path, ...]:
        raise NotImplementedError
