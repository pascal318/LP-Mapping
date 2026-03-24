from __future__ import annotations

import csv
import io
from collections import defaultdict
from typing import Iterable

import pandas as pd

from .adapters import ExcelSourceAdapter
from .investor_classification import is_likely_individual_investor
from .models import (
    CompanyExposureRow,
    CompanyInvestor,
    IndividualInvestor,
    InvestorMatch,
    LPFundPair,
    LPRecord,
    SourceAdapter,
    UnmatchedInvestor,
)
from .matching import InvestorMatcher


class LookupService:
    def __init__(self, adapter: SourceAdapter | None = None) -> None:
        self.adapter = adapter or ExcelSourceAdapter()
        self.lp_fund_pairs = tuple(self.adapter.load_lp_fund_pairs())
        self.lp_records = tuple(self.adapter.load_unique_lps())
        self.company_investors = tuple(self.adapter.load_company_investors())

        self._lp_by_name = self._build_lp_index(self.lp_records, self.lp_fund_pairs)
        self._fund_manager_to_pairs = self._build_fund_manager_index(self.lp_fund_pairs)
        self._company_to_investors = self._build_company_investor_index(self.company_investors)
        self.matcher = InvestorMatcher(self._fund_manager_to_pairs.keys())

        self._individuals_by_company: dict[str, list[IndividualInvestor]] = defaultdict(list)
        self._matches_by_company: dict[str, list[InvestorMatch]] = defaultdict(list)
        self._unmatched_by_company: dict[str, list[UnmatchedInvestor]] = defaultdict(list)
        self._exposures_by_company: dict[str, list[CompanyExposureRow]] = defaultdict(list)
        self._build_lookup_tables()

    @staticmethod
    def _build_lp_index(lp_records: Iterable[LPRecord], lp_fund_pairs: Iterable[LPFundPair]) -> dict[str, LPRecord]:
        lp_by_name = {record.lp_name: record for record in lp_records}
        for pair in lp_fund_pairs:
            lp_by_name.setdefault(
                pair.lp_name,
                LPRecord(
                    lp_name=pair.lp_name,
                    lp_type=pair.lp_type,
                    city=pair.city,
                    country=pair.country,
                ),
            )
        return lp_by_name

    @staticmethod
    def _build_fund_manager_index(lp_fund_pairs: Iterable[LPFundPair]) -> dict[str, list[LPFundPair]]:
        by_manager: dict[str, list[LPFundPair]] = defaultdict(list)
        for pair in lp_fund_pairs:
            by_manager[pair.fund_manager].append(pair)
        return by_manager

    @staticmethod
    def _build_company_investor_index(company_investors: Iterable[CompanyInvestor]) -> dict[str, list[CompanyInvestor]]:
        by_company: dict[str, list[CompanyInvestor]] = defaultdict(list)
        for item in company_investors:
            by_company[item.company].append(item)
        return by_company

    def _build_lookup_tables(self) -> None:
        for company, investors in self._company_to_investors.items():
            exposure_accumulator: dict[str, dict[str, object]] = {}
            for investor in investors:
                match_result = self.matcher.match(company=company, raw_investor=investor.raw_investor)
                if match_result.matches:
                    self._matches_by_company[company].extend(match_result.matches)
                    for match in match_result.matches:
                        for pair in self._fund_manager_to_pairs.get(match.matched_fund_manager, []):
                            lp_record = self._lp_by_name[pair.lp_name]
                            state = exposure_accumulator.setdefault(
                                pair.lp_name,
                                {
                                    "matched_investors": set(),
                                    "best_score": 0,
                                    "lp_type": lp_record.lp_type,
                                    "city": lp_record.city,
                                    "country": lp_record.country,
                                },
                            )
                            state["matched_investors"].add(match.matched_fund_manager)
                            state["best_score"] = max(int(state["best_score"]), match.match_score)
                elif is_likely_individual_investor(investor.raw_investor):
                    self._individuals_by_company[company].append(
                        IndividualInvestor(
                            company=company,
                            raw_investor=investor.raw_investor,
                        )
                    )
                else:
                    self._unmatched_by_company[company].append(
                        UnmatchedInvestor(
                            company=company,
                            raw_investor=investor.raw_investor,
                            best_candidate=match_result.best_candidate,
                            best_score=match_result.best_score,
                        )
                    )

            self._exposures_by_company[company] = [
                CompanyExposureRow(
                    company=company,
                    lp_name=lp_name,
                    matched_investors=tuple(sorted(state["matched_investors"])),
                    best_score=int(state["best_score"]),
                    lp_type=str(state["lp_type"]),
                    city=str(state["city"]),
                    country=str(state["country"]),
                )
                for lp_name, state in sorted(exposure_accumulator.items())
            ]
            self._matches_by_company[company].sort(
                key=lambda item: (item.raw_investor.lower(), -item.match_score, item.matched_fund_manager.lower())
            )
            self._individuals_by_company[company].sort(key=lambda item: item.raw_investor.lower())
            self._unmatched_by_company[company].sort(key=lambda item: item.raw_investor.lower())

    @property
    def source_paths(self) -> tuple[str, ...]:
        return tuple(str(path) for path in self.adapter.source_paths)

    def list_companies(self) -> list[str]:
        return sorted(self._company_to_investors)

    def company_summary(self, company: str) -> dict[str, int]:
        matched_investors = {match.raw_investor for match in self._matches_by_company.get(company, [])}
        individual_investors = {item.raw_investor for item in self._individuals_by_company.get(company, [])}
        unmatched_investors = {item.raw_investor for item in self._unmatched_by_company.get(company, [])}
        return {
            "matched_investors": len(matched_investors),
            "individual_investors": len(individual_investors),
            "unmatched_investors": len(unmatched_investors),
            "deduped_lps": len(self._exposures_by_company.get(company, [])),
        }

    def get_exposure_rows(self, company: str) -> list[CompanyExposureRow]:
        return list(self._exposures_by_company.get(company, []))

    def get_match_rows(self, company: str) -> list[InvestorMatch]:
        return list(self._matches_by_company.get(company, []))

    def get_individual_rows(self, company: str) -> list[IndividualInvestor]:
        return list(self._individuals_by_company.get(company, []))

    def get_unmatched_rows(self, company: str) -> list[UnmatchedInvestor]:
        return list(self._unmatched_by_company.get(company, []))

    def exposure_dataframe(self, company: str) -> pd.DataFrame:
        rows = [
            {
                "LP Name": row.lp_name,
                "Matched Investor(s)": ", ".join(row.matched_investors),
                "Best Match Score": row.best_score,
                "LP Type": row.lp_type,
                "City": row.city,
                "Country": row.country,
            }
            for row in self.get_exposure_rows(company)
        ]
        return pd.DataFrame(rows)

    def match_dataframe(self, company: str) -> pd.DataFrame:
        rows = [
            {
                "Raw Investor": row.raw_investor,
                "Matched Fund Manager": row.matched_fund_manager,
                "Match Method": row.match_method,
                "Match Score": row.match_score,
            }
            for row in self.get_match_rows(company)
        ]
        return pd.DataFrame(rows)

    def individual_dataframe(self, company: str) -> pd.DataFrame:
        rows = [
            {
                "Raw Investor": row.raw_investor,
            }
            for row in self.get_individual_rows(company)
        ]
        return pd.DataFrame(rows)

    def unmatched_dataframe(self, company: str) -> pd.DataFrame:
        rows = [
            {
                "Raw Investor": row.raw_investor,
            }
            for row in self.get_unmatched_rows(company)
        ]
        return pd.DataFrame(rows)

    def exposure_csv_bytes(self, company: str) -> bytes:
        dataframe = self.exposure_dataframe(company)
        buffer = io.StringIO()
        dataframe.to_csv(buffer, index=False, quoting=csv.QUOTE_MINIMAL)
        return buffer.getvalue().encode("utf-8")
