# Silence or Salience: Replication Package

This repository contains the code and data for the working paper
**"Silence or Salience? Aid Dependency and Media Reaction to the USAID
Shutdown"**. It measures how fast and how much news coverage of the
USAID funding freeze appeared for each country in GDELT news-event data
(20 January 2025 to 20 January 2026), and tests whether countries that
received more US aid got faster and more coverage.

---

## Repo Structure

```
README.md              this file
DATA_DICTIONARY.md     every column of every data file, with units
INVENTORY.md           where each file came from in the original project
requirements.txt       Python packages (pinned versions)
config.py              all file paths; every script reads its paths from here
run_all.sh             runs the whole pipeline in order

data/
  raw/                 empty in the repo; GDELT downloads go here
  input/               small input files (aid data, country codes, WDI snapshot)
  intermediate/        files made from the raw GDELT data (included, so you
                       do not need to download GDELT for the main tables)
src/                   the main pipeline, numbered in run order (00 to 05)
robustness/            robustness checks and build_all.py, the final table builder
outputs/               empty in the repo; every script writes its results here
exploratory/           exploratory checks that are not in the paper (tone and goldstein,
                       press freedom, coverage intensity, US-specific aid dependency)
```

---

## Quick start 

You need **Python 3.13** (the original work used 3.13.3). Check with
`python3.13 --version`. The commands are for macOS or Linux. On Windows,
use `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

Run all commands from the repository root (the folder with this file).

**Step 1. Make a virtual environment and install the packages.**

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Step 2. Run the three scripts that need only the included data.**

```bash
python src/04b_merge_outcomes.py
python src/05_paper_tables.py
python robustness/phase3_robustness.py
```

| Command | What it does | Files it creates |
|---|---|---|
| `src/04b_merge_outcomes.py` | Rebuilds the main analysis file from the aid spreadsheet and checks it cell by cell against the included copy. It prints `differing: 0` if all is correct. | `outputs/04b_merge_outcomes/3-29-v2_oda_data.csv` |
| `src/05_paper_tables.py` | Makes the original versions of Tables 1–4, A1–A2 and Figures 1–2, A1–A2. | `outputs/05_paper_tables/`: 6 table CSVs, 4 figure PNGs, 2 data-check TXT files |
| `robustness/phase3_robustness.py` | Runs robustness checks: classical vs. robust (HC3) standard errors, a volume control, other forms of the attention share, a Sub-Saharan Africa split, outlier re-runs and a Cox model. | `outputs/phase3_robustness/phase3_summary_table.csv` and `log.txt` |

**Step 3 (optional, about 195 MB download). Make the final tables.**
`build_all.py` makes the final version of every table and figure. One
table (B5) needs 26 GDELT daily files, so download them first:

```bash
python src/01_download_gdelt.py --start 2025-06-01 --end 2025-07-14
python robustness/build_all.py
```

- The download command asks for 44 days. 26 files download. The other
  18 days do not exist at GDELT; the script prints "HTTP 404 (expected)"
  for each of them. This is correct.
- The download time depends on your connection. In our test, the 26
  files (about 195 MB) took about 45 seconds.
- `build_all.py` takes about 30 seconds. It writes to
  `outputs/build_all/`: the table CSVs, the figure PNGs, `manifest.csv`,
  `diff_report.txt` and `log.txt`.
- Without the V-Dem and Voeten files (section 6), `build_all.py` skips
  Tables 5–10, A3–A5 and Figures 3–6. It does not stop; it lists them
  under FAILURES at the end of its output.

`bash run_all.sh` runs steps 2 and 3 and
all other robustness scripts. Some of those scripts need the internet
(GDELT file list, World Bank API) and the V-Dem / Voeten files.

---

## Full rebuild from raw GDELT data (optional)

You need this only if you want to rebuild the files (size: 348 files, about 2.4 GB in total) in
`data/intermediate/` yourself.

GDELT has no files for the 18 days
**2025-06-14 to 2025-07-01**. The server returns HTTP 404 for them, and
they are not in GDELT's own file list. The download script expects these
18 404s and stops with an error only if any *other* day is missing. The
full period has 366 days, so you get 348 files.

```bash
# 1. Download all 348 files to data/raw/ and write data/raw/MANIFEST.csv
python src/01_download_gdelt.py

# 2. The search does not overwrite an existing result. Move the included file away first.
mv data/intermediate/usaid_closure_v1/matches_rows.csv matches_rows.included.csv

# 3. Keyword search -> data/intermediate/usaid_closure_v1/matches_rows.csv
python src/02_search.py

# 4. Country and region mapping (needs internet) -> data/intermediate/usaid_final_geography.csv
python src/03_map.py

# 5. Country-level counts and days to first article -> data/intermediate/country_reaction_dataset.csv
python src/04_build_dataset.py

# 6. Unique-URL counts per country -> data/intermediate/total_articles_unique_url.csv
python robustness/phase3_dedup_full_corpus.py
```

Steps 5 and 6 overwrite the included files. Then run the quick-start
scripts again.

Important: the main analysis file `data/input/3-29-v2_oda_data.csv`
is made from the aid spreadsheet, not from the files that steps 3–6
make. A full rebuild therefore does not change Tables 1–4 of
`05_paper_tables.py`.

The search was checked on 5 days (558 rows, byte-identical to the
included file). A full 348-day search was not run in this package.

`bash run_all.sh --full` runs steps 1, 4, 5 and 6, then all analysis
scripts. It runs the search (step 3) only if `matches_rows.csv` is not
there.

---

## What each script does

| # | Script | What it does |
|---|---|---|
| 0 | `src/00_filter_vdem.py` | Keeps the 5 V-Dem columns that the project uses (press censorship, harassment of journalists). Needs the V-Dem download. |
| 0 | `src/00_filter_idealpoint.py` | Keeps the 5 columns of the Voeten UN-voting data that the project uses. Needs the Voeten download. |
| 1 | `src/01_download_gdelt.py` | Downloads the GDELT 1.0 daily Event files, skips files you already have, and writes a SHA-256 list (`MANIFEST.csv`). |
| 2 | `src/02_search.py` | Keeps the GDELT rows that contain a USAID marker (`USAID`, `USAGOVDEV`) **and** a disruption word (freeze, pause, cut, shutdown, closure, halt, suspend, suspension, defund, ...). It stops if its output file already exists. |
| 3 | `src/03_map.py` | Maps each matched row to a country and a UN region. No table uses its output. |
| 4 | `src/04_build_dataset.py` | Counts, for each country, all GDELT rows and matched rows, and the days from 20 January 2025 to the first matched row. |
| 4a | `robustness/phase3_dedup_full_corpus.py` | Counts unique article URLs for each country in all GDELT data (the denominator of the unique-URL attention share). |
| 4b | `src/04b_merge_outcomes.py` | Rebuilds the main analysis file `3-29-v2_oda_data.csv` from the aid spreadsheet and checks it against the included copy. |
| 5 | `src/05_paper_tables.py` | Makes the original Tables 1–4, A1–A2 and Figures 1–2, A1–A2 (ordinary standard errors, raw-row attention share). |
| 6 | `robustness/oda_controls_only.py` | Original control-variable checks: press freedom (V-Dem) and alignment with the US (Voeten). Stops if the V-Dem / Voeten files are missing. |
| 7 | `robustness/phase3_robustness.py` | Robustness checks: robust (HC3) standard errors, volume control, other forms of the attention share, Sub-Saharan Africa split, outlier re-runs, Cox model. |
| 8 | `robustness/sensitivity_analysis.py`, `robustness/followup_sensitivity.py` | Test how much the 18 missing days could change the results. Need the 26 neighbor-day files and the internet. |
| 9 | `robustness/analysis.py`, `analysis2.py`, `analysis3.py` | Further checks (small counts, population and GDP controls, median split, news domains). Download World Bank data each time they run. |
| 10 | `robustness/build_all.py` | **Final table builder.** Makes every table and figure in its final form (robust HC3 standard errors, unique-URL attention share, Africa split into Sub-Saharan and Northern). |

### Which script makes which paper table

This package does not include the paper, so it does not say which
version the paper prints. `build_all.py` makes the final version. The
earlier version comes from `05_paper_tables.py` (Tables 1–4, A1–A2,
Figures 1–2, A1–A2) or `oda_controls_only.py` (Tables 5–10, A3–A5,
Figures 3–6).

| Paper item | `outputs/build_all/` file |
|---|---|
| Tables 1–4 | `table1_descriptive_days.csv`, `table2_descriptive_attention.csv`, `table3_regression_days_main.csv`, `table4_regression_attention_main.csv` |
| Tables 5–6 (press freedom) | `table5_press_freedom_days.csv`, `table6_press_freedom_attention.csv` |
| Tables 7–10 (US alignment) | `table7_alignment_days.csv`, `table8_alignment_attention.csv`, `table9_simple_slopes_days.csv`, `table10_simple_slopes_attention.csv` |
| Tables A1–A5 | `tableA1_regression_days_by_region.csv`, `tableA2_regression_attention_by_region.csv`, `tableA3_press_freedom_by_region.csv`, `tableA4_alignment_by_region.csv`, `tableA5_alignment_drop_europe_oceania.csv` |
| Tables B1–B10 | `tableB1_volume_control.csv`, `tableB2_cox_models.csv`, `tableB3_negative_binomial.csv`, `tableB4_no_article_countries.csv` (+ `_profile.csv`), `tableB5_data_gap.csv`, `tableB6_median_split.csv`, `tableB7_ssa_interaction.csv`, `tableB8_raw_row_attention.csv`, `tableB9_top50_domains.csv`, `tableB10_matched_url_counts.csv` |
| Figures 1–6, A1–A2 | `figure1_days_main.png` … `figure6_alignment_attention.png`, `figureA1_days_by_region.png`, `figureA2_attention_by_region.png` |

The earlier versions have the same file names in
`outputs/05_paper_tables/` and `outputs/oda_controls_only/`.

---

## The Data

Full column lists with units: [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

### Included files

| File | Source | Important columns |
|---|---|---|
| `data/input/3-29-v2_oda_data.csv` | Made from the aid spreadsheet below (rebuilt by `04b`). 102 countries. | `us_oda_disbursements`: US aid, USD millions (definition still to be confirmed). `attention_share`: matched rows ÷ all GDELT rows for the country. `days_to_first_article`: days from 20 January 2025 to the first matched row (empty = no match). |
| `data/input/3_29__oda_data.csv` and `.xlsx` | Aid spreadsheet compiled for the project. Its header names OECD DAC2A (measure 206), 2018–2022, as the aid source. | 143 countries; aid and GDELT columns. |
| `data/input/country-codes.csv` | Country-code crosswalk. The project files do not record where it came from. | `FIPS` (the code GDELT uses) → `ISO3166-1-Alpha-3`; UN region names. |
| `data/input/wdi_population_gdp.csv` | World Bank WDI, downloaded 2026-10-05 (see attribution below). No script reads it; it is a frozen copy. | `population_avg`, `gdp_avg` (current USD), mean of 2018–2022. |
| `data/intermediate/usaid_closure_v1/matches_rows.csv` | Made by `02_search.py` from GDELT 1.0. 12,017 rows. | `date` plus the 58 GDELT columns (`col_0` … `col_57`). `col_51` = country of the event location; `col_57` = article URL. |
| `data/intermediate/country_reaction_dataset.csv` | Made by `04_build_dataset.py`. 236 countries. | `total_articles`, `usaid_articles` (GDELT row counts), `attention_share`, `days_to_first_article`. |
| `data/intermediate/total_articles_unique_url.csv` | Made by `phase3_dedup_full_corpus.py`. 236 countries. | `total_articles_unique_url`: unique article URLs per country. |

GDELT 1.0 daily Event files come from http://data.gdeltproject.org/events/
(file names `YYYYMMDD.export.CSV.zip`).

### Files that are not included (download them yourself)

These files are not in the repository because of their redistribution terms. You need them only for the press-freedom and
US-alignment checks (Tables 5–10, A3–A5, Figures 3–6). 

**V-Dem (press freedom)**
1. Get the Varieties of Democracy (V-Dem) Country-Year Dataset **v12**,
   "Country-Year: V-Dem Core", CSV version. DOI:
   https://doi.org/10.23696/vdemds22. Older versions are on
   https://www.v-dem.net/data/dataset-archive/ (check this link).
2. Put the file `V-Dem-CY-Core-v12.csv` (about 196 MB) in `data/raw/`.
3. Run `python src/00_filter_vdem.py`. It writes `data/input/vdem_filtered.csv`.
4. Cite V-Dem as its "Suggested Citation v12" document says.

**Voeten UN General Assembly ideal points (US alignment)**
1. Get "United Nations General Assembly Ideal Point Estimates,
   1946-2025" by Erik Voeten from https://dataverse.harvard.edu/dataverse/Voeten.
   The exact Dataverse version used was not recorded.
2. Put the file `IdealpointestimatesFP_2026FP.csv` (about 1.4 MB) in `data/raw/`.
3. Run `python src/00_filter_idealpoint.py`. It writes `data/input/idealpoint_filtered.csv`.
4. Cite: Bailey, Michael A., Anton Strezhnev, and Erik Voeten. "Estimating
   Dynamic State Preferences from United Nations Voting Data." *Journal of
   Conflict Resolution* 61, no. 2 (2017): 430–456.

Then run `python robustness/oda_controls_only.py` and
`python robustness/build_all.py` again.

### World Bank WDI attribution

`data/input/wdi_population_gdp.csv` contains data from The World Bank,
World Development Indicators (indicators `SP.POP.TOTL` and
`NY.GDP.MKTP.CD`), downloaded on 2026-10-05 from `api.worldbank.org`.
License: Creative Commons Attribution 4.0 International (CC BY 4.0),
https://creativecommons.org/licenses/by/4.0/. The values are 2018–2022
means computed by this project; they are not World Bank figures.
`robustness/analysis.py`, `analysis2.py` and `analysis3.py` download WDI
data again each time they run, so their results can change if the World
Bank revises its data.
