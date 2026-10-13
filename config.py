# all file paths for the project, relative to the repo root (the folder of this file)
# reads: nothing. scripts in src/ and robustness/ import it
# writes: makes the folders under outputs/ if they are missing
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# data folders
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # gdelt daily zips and third-party raw downloads
INPUT_DIR = DATA_DIR / "input"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
OUTPUTS_DIR = ROOT / "outputs"

# raw data (not in the repo, see the readme)
GDELT_DIR = RAW_DIR  # one zip per day, named by date
GDELT_MANIFEST = RAW_DIR / "MANIFEST.csv"
VDEM_RAW = RAW_DIR / "V-Dem-CY-Core-v12.csv"
IDEALPOINT_RAW = RAW_DIR / "IdealpointestimatesFP_2026FP.csv"

# inputs
ODA_DATA = INPUT_DIR / "3-29-v2_oda_data.csv"
ODA_SOURCE_SHEET_CSV = INPUT_DIR / "3_29__oda_data.csv"
ODA_SOURCE_SHEET_XLSX = INPUT_DIR / "3_29__oda_data.xlsx"
COUNTRY_CODES = INPUT_DIR / "country-codes.csv"
WDI_SNAPSHOT = INPUT_DIR / "wdi_population_gdp.csv"
VDEM_FILTERED = INPUT_DIR / "vdem_filtered.csv"              # made by src/00_filter_vdem.py
IDEALPOINT_FILTERED = INPUT_DIR / "idealpoint_filtered.csv"  # made by src/00_filter_idealpoint.py

# intermediate files
SEARCH_OUTPUT_DIR = INTERMEDIATE_DIR          # 02_search.py writes <query name>/matches_rows.csv here
MATCHES_ROWS = INTERMEDIATE_DIR / "usaid_closure_v1" / "matches_rows.csv"
USAID_GEOGRAPHY = INTERMEDIATE_DIR / "usaid_final_geography.csv"   # made by 03_map.py (not shipped)
COUNTRY_REACTION = INTERMEDIATE_DIR / "country_reaction_dataset.csv"
TOTAL_UNIQUE_URL = INTERMEDIATE_DIR / "total_articles_unique_url.csv"

# output folders, one per script
OUT_PAPER_TABLES = OUTPUTS_DIR / "05_paper_tables"
OUT_CONTROLS = OUTPUTS_DIR / "oda_controls_only"
OUT_PHASE3 = OUTPUTS_DIR / "phase3_robustness"
OUT_SENSITIVITY = OUTPUTS_DIR / "sensitivity"          # sensitivity_analysis.py + followup_sensitivity.py
OUT_ANALYSIS_V5 = OUTPUTS_DIR / "analysis_v5"          # analysis.py, analysis2.py, analysis3.py
OUT_BUILD_ALL = OUTPUTS_DIR / "build_all"

for _d in (OUT_PAPER_TABLES, OUT_CONTROLS, OUT_PHASE3,
           OUT_SENSITIVITY, OUT_ANALYSIS_V5, OUT_BUILD_ALL):
    _d.mkdir(parents=True, exist_ok=True)
