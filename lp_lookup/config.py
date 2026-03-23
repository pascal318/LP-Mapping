from pathlib import Path

LP_DATABASE_PATH = Path("/Users/pascalsuhrcke/Downloads/Atrea_LP_Database_Export.xlsx")
COMPANY_LOOKUP_PATH = Path("/Users/pascalsuhrcke/Downloads/Company Look-Up.xlsx")

LP_FUND_PAIR_SHEET = "All LP-Fund Pairs"
UNIQUE_LPS_SHEET = "Unique LPs"
COMPANY_FUND_MAP_SHEET = "Company-Fund Map"

LP_FUND_PAIR_HEADERS = (
    "Fund Manager",
    "LP Name",
    "LP Type",
    "City",
    "Country",
)

UNIQUE_LP_HEADERS = (
    "LP Name",
    "LP Type",
    "City",
    "Country",
)

COMPANY_LOOKUP_HEADERS = (
    "Company",
    "Lead Investors",
)

FUZZY_SCORE_FLOOR = 70
FUZZY_SCORE_MARGIN = 3
