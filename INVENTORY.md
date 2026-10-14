# INVENTORY: gdelt_ra → gdelt_ra_replication

Source: `<project root>` (read-only).
Date of inventory: 2026-10-13. Status: **approved; copy built**.

Sizes are in bytes. "→" shows the planned path in the copy.

---

## 1. INCLUDE (final, after approval on 2026-10-13)

### 1.1 Scripts

| Source file | Size | Copy path |
|---|---:|---|
| `gdelt_searcher.py` | 6,610 | `src/02_search.py` |
| `gdelt_mapper.py` | 3,667 | `src/03_map.py` |
| `reg_ready.py` | 5,069 | `src/04_build_dataset.py` |
| `scatterplotting/aug_7_attempt.py` | 19,430 | `src/05_paper_tables.py` |
| `control_regs/01_scripts/filter_vdem_columns.py` | 1,867 | `src/00_filter_vdem.py` (A6) |
| `control_regs/01_scripts/filter_idealpoint_columns.py` | 1,862 | `src/00_filter_idealpoint.py` (A6) |
| `control_regs/oda_controls_only.py` | 26,097 | `robustness/oda_controls_only.py` |
| `outputs_v3/phase3_robustness.py` | 26,866 | `robustness/phase3_robustness.py` |
| `outputs_v3/phase3_dedup_full_corpus.py` | 2,032 | `robustness/phase3_dedup_full_corpus.py` |
| `outputs_v4/sensitivity_analysis.py` | 15,183 | `robustness/sensitivity_analysis.py` |
| `outputs_v4/followup_sensitivity.py` | 13,034 | `robustness/followup_sensitivity.py` |
| `outputs_v5/analysis.py` | 18,319 | `robustness/analysis.py` |
| `outputs_v5/analysis2.py` | 18,504 | `robustness/analysis2.py` |
| `outputs_v5/analysis3.py` | 13,192 | `robustness/analysis3.py` |
| `outputs_v6/build_all.py` | 68,485 | `robustness/build_all.py` (final table builder) |

Sizes are of the source files. The copies are larger (header comment,
config import). Allowed code changes: see README.md.

### 1.2 Input data

| Source file | Size | Copy path |
|---|---:|---|
| `scatterplotting/3-29-v2_oda_data.csv` | 3,972 | `data/input/3-29-v2_oda_data.csv` |
| `country-codes.csv` | 134,304 | `data/input/country-codes.csv` |
| `scatterplotting/3_29__oda_data.csv` | 18,840 | `data/input/3_29__oda_data.csv` (A7) |
| `scatterplotting/3_29__oda_data.xlsx` | 31,913 | `data/input/3_29__oda_data.xlsx` (A7) |
| `outputs_v5/wdi_population_gdp.csv` | 4,290 | `data/input/wdi_population_gdp.csv` (A5; CC BY 4.0 snapshot) |

### 1.3 Intermediate data

| Source file | Size | Copy path |
|---|---:|---|
| `outputs/usaid_closure_v1/matches_rows.csv` | 4,928,709 | `data/intermediate/usaid_closure_v1/matches_rows.csv` |
| `country_reaction_dataset.csv` | 16,617 | `data/intermediate/country_reaction_dataset.csv` |
| `outputs_v3/phase3_robustness/total_articles_unique_url.csv` | 2,222 | `data/intermediate/total_articles_unique_url.csv` |

`matches_rows.csv` keeps its `usaid_closure_v1/` subfolder, because
`src/02_search.py` writes to `<output dir>/<query name>/matches_rows.csv`
and its logic is unchanged.

### 1.4 New files (not in the source)

| Copy path | What |
|---|---|
| `README.md`, `INVENTORY.md`, `DATA_DICTIONARY.md` | documentation |
| `requirements.txt` | pinned packages (Python 3.13) |
| `run_all.sh` | pipeline runner |
| `.gitignore` | ignore rules |
| `config.py` | all paths |
| `src/01_download_gdelt.py` | new GDELT downloader (replaces `gdelt_scraper.py`) |
| `src/04b_merge_outcomes.py` | new: rebuilds `3-29-v2_oda_data.csv` from `3_29__oda_data.csv` (exact match, 612 cells) |
| `data/raw/.gitkeep`, `outputs/.gitkeep` | keep empty folders |
| `exploratory/tone_goldstein/PREDICTIONS.md` | exploratory: predictions, written before the models ran |
| `exploratory/tone_goldstein/run_tone_goldstein.py` | exploratory: tone and goldstein regressions (not in the paper) |
| `exploratory/tone_goldstein/results.csv`, `exploratory/tone_goldstein/descriptives.csv`, `exploratory/tone_goldstein/log.txt` | exploratory: outputs of `run_tone_goldstein.py` |
| `exploratory/press_freedom/PREDICTIONS.md` | exploratory: predictions, written before the models ran |
| `exploratory/press_freedom/run_press_freedom.py` | exploratory: v-dem press freedom interaction (not in the paper) |
| `exploratory/press_freedom/results.csv`, `exploratory/press_freedom/log.txt` | exploratory: outputs of `run_press_freedom.py` |
| `exploratory/coverage_intensity/PREDICTIONS.md` | exploratory: predictions, written before the models ran |
| `exploratory/coverage_intensity/run_coverage_intensity.py` | exploratory: coverage intensity (not in the paper) |
| `exploratory/coverage_intensity/results.csv`, `exploratory/coverage_intensity/log.txt` | exploratory: outputs of `run_coverage_intensity.py` |
| `exploratory/us_specific_aid/run_us_specific_aid.py` | exploratory: US-specific vs general aid dependency (not in the paper). From `usaid_aid_dependency_replication/run_analysis.py`, a standalone extension received 2026-10-14. Changed only: paths from `config.py`, outputs to its folder, `log.txt` |
| `exploratory/us_specific_aid/README.md` | exploratory: the extension's README (specification and caveats), with run instructions for this repo |
| `exploratory/us_specific_aid/us_specific_results.csv`, `exploratory/us_specific_aid/analysis_sample.csv`, `exploratory/us_specific_aid/log.txt` | exploratory: outputs of `run_us_specific_aid.py`. Results are byte-identical to the unmodified `run_analysis.py` on this repo, and match the extension's shipped `results/us_specific_results.csv` to 4.4e-13 (relative) |
| `exploratory/us_specific_aid/run_us_specific_aid_checks.py` | exploratory: new follow-up checks on the extension (unique-URL counts, collinearity and joint test, negative net aid) |
| `exploratory/us_specific_aid/checks_results.csv`, `checks_collinearity.csv`, `checks_negative_aid.csv`, `checks_log.txt` | exploratory: outputs of `run_us_specific_aid_checks.py` |

A first version of `04b` (outcomes from `country_reaction_dataset.csv`)
did not match exactly (3 cells, 0.000001).

## 2. EXCLUDE

### 2.1 Large, generated or system files

| Path | Size | Reason |
|---|---:|---|
| `gdelt_events/` (348 zips) | 2.4 GB | Raw GDELT. `01_download_gdelt.py` gets them again. |
| `.venv/`, `control_regs/.venv/`, `oda_analysis/.venv/`, `scatterplotting/.venv/` | 456 MB / 367 MB / 284 MB / 337 MB | Virtual environments. |
| `.git/` | 2.4 GB | Git history. It contains the 348 zips (they are committed). You will run `git init` in the copy. |
| `__pycache__/` (none found outside .venv) | (none) | Cache. |
| `.DS_Store` (9 files) | 6–14 KB | macOS system files. |

### 2.2 Logs and console captures

`outputs_v3/log.txt`, `outputs_v3/phase1_console.txt`,
`outputs_v3/phase1_controls_console.txt`,
`outputs_v3/phase3_dedup_full_corpus_console.txt`, `outputs_v4/log.txt`,
`outputs_v4/followup_log.txt`, `outputs_v5/log.txt`, `outputs_v5/log2.txt`,
`outputs_v5/log3.txt`, `outputs_v6/log.txt`. Reason: logs. They also
contain the absolute path `<project root>`.

### 2.3 Placeholder (mock) data

| Path | Size | Reason |
|---|---:|---|
| `ODA Donor Dependency Analysis Sample.xlsx` | 15,513 | Mock data. |
| `ODA Donor Dependency Analysis Sample (1).xlsx` | 31,216 | Mock data (copy). |
| `oda_analysis/ODA Donor Dependency Analysis Sample.xlsx` | 31,216 | Mock data (third copy, not named in your list). |
| `Aid Dependency & Reaction Dataset.csv` | 18,676 | Mock data. |
| `Aid Dependency & Reaction Dataset (1).csv` | 18,676 | Mock data (copy). |

### 2.4 Old near-duplicate scripts

| Old script | Size | Replaced by |
|---|---:|---|
| `outputs_v3/phase1_run.py` | 19,485 | `scatterplotting/aug_7_attempt.py`. Diff: only lines 69–70 (absolute paths). |
| `outputs_v3/phase1_controls_run.py` | 26,187 | `control_regs/oda_controls_only.py`. Diff: only lines 61–64 (absolute paths). |
| `control_regs/produce_tables_figures.py` | 18,685 | `control_regs/oda_controls_only.py` (older, 2026-08-07; no Tables 9–10, A5). |
| `scatterplotting/june_1_attempt.py` | 20,015 | `aug_7_attempt.py` |
| `scatterplotting/tempCodeRunnerFile.py` | 20,015 | `aug_7_attempt.py` (byte-identical to `june_1_attempt.py`) |
| `scatterplotting/reg_days_by_region.py` | 20,968 | `aug_7_attempt.py` |
| `scatterplotting/reg_w_labels.py` | 7,438 | `aug_7_attempt.py` |
| `scatterplotting/reg_4-28.py` | 5,129 | `aug_7_attempt.py` |
| `scatterplotting/sc_plot.py` | 3,854 | `aug_7_attempt.py` |
| `scatterplotting/confirm.py` | 3,940 | `aug_7_attempt.py` (data overview printout only) |
| `tempCodeRunnerFile.py` | 78 | Editor fragment (one line of `gdelt_grapher.py`). |
| `oda_analysis/tempCodeRunnerFile.py` | 2 | Empty editor fragment. |
| `oda_analysis/oda_mapper.py` | 7,772 | No replacement. It maps the mock xlsx only. |

### 2.5 Duplicate data

| Path | Size | Reason |
|---|---:|---|
| `usaid_closure_matches_rows_v1.csv` | 4,928,709 | Byte-identical to `outputs/usaid_closure_v1/matches_rows.csv`. |
| `control_regs/3-29-v2_oda_data.csv` | 3,972 | Byte-identical to `scatterplotting/3-29-v2_oda_data.csv`. |

### 2.6 Generated outputs (the copy makes them again in `outputs/`)

- All tables and figures in `outputs_v3/phase1_controls/`,
  `outputs_v3/phase1_reproduction/`, `outputs_v3/phase3_robustness/phase3_summary_table.csv`,
  `outputs_v4/*.csv`, `outputs_v5/*.csv` (except see ASK A5),
  `outputs_v6/*.csv`, `outputs_v6/*.png`, `outputs_v6/manifest.csv`,
  `outputs_v6/diff_report.txt`, `control_regs/outputs/`,
  `scatterplotting/outputs/`, `scatterplotting/fig_*.png`,
  `scatterplotting/regression_*.png`.
- Root figures: `Figure_1.png` … `Figure_4.png`, `figure_5.png`,
  `fig1-416.png`, `fig2-416.png`, `reaction_timeline.png`.
- `oda_analysis/ne_110m_admin_0_countries.*` (Natural Earth shapefile,
  ~756 KB): only the mock-data map script uses it.

### 2.7 Items in your EXCLUDE rules that I did not find

I found **no** paper draft PDFs, no `figures_v2.pdf`, no screenshots, no
emails and no co-author correspondence in the source folder. The only
PDFs are the four V-Dem documentation PDFs (see ASK A3).

---

## 3. ASK: decisions (2026-10-13)

| Item | Decision |
|---|---|
| A1 `gdelt_scraper.py` | Not copied. `src/01_download_gdelt.py` replaces it. |
| A2 `gdelt_grapher.py`, `usaid_final_geography.csv` | Not copied. |
| A3 V-Dem (raw CSV, `vdem_filtered.csv`, 4 PDFs) | Not copied. Download steps in README.md. |
| A4 Voeten (`IdealpointestimatesFP_2026FP.csv`, codebook, `idealpoint_filtered.csv`) | Not copied. Download steps in README.md. |
| A5 `wdi_population_gdp.csv` | Copied as a snapshot, with CC BY 4.0 attribution in README.md. |
| A6 filter scripts | Copied as `src/00_filter_vdem.py`, `src/00_filter_idealpoint.py`. |
| A7 `3_29__oda_data.csv` / `.xlsx` | Copied to `data/input/`. |
| A8 Table B5 neighbor zips | WARNING printed for each missing zip. |

## 4. Other findings

- No original script makes `3-29-v2_oda_data.csv` (now rebuilt by `src/04b_merge_outcomes.py`). Its `attention_share` and
  `days_to_first_article` columns have no code path in the source folder.
- `3-29-v2_oda_data.csv` stores some numbers as text with a thousands
  comma (for example `"2,128.8"` for Ukraine).
- `gdelt_searcher.py` line 73: three lines were merged into one comment,
  so `TIMEOUT` and `DL_CHUNK` are never defined. They are not used, so
  there is no error.
- `gdelt_searcher.py` appends to `matches_rows.csv`. A second run without
  deleting the file doubles the rows.
- `gdelt_mapper.py` and `gdelt_grapher.py` download a FIPS crosswalk from
  GitHub (mysociety/gaze) at run time. `reg_ready.py` uses the local
  `country-codes.csv` instead.
- Two Python versions: root `.venv` is Python 3.13.3;
  `control_regs/.venv` is Python 3.11.4.
- Secret search (`key`, `token`, `secret`, `password`, `@`, `api`): no
  keys, tokens, passwords or emails in any script. Only hits: absolute
  paths `<project root>` in 8 scripts and in the logs,
  and public URLs (`api.worldbank.org`, `data.gdeltproject.org`).

---

## 5. Full source listing (bytes)

Folders summarized, not listed file by file: `.git/` 2.4 GB;
`gdelt_events/` 2.4 GB (348 files, `20250120.export.CSV.zip` …);
`.venv/` 456 MB; `control_regs/.venv/` 367 MB; `oda_analysis/.venv/`
284 MB; `scatterplotting/.venv/` 337 MB. Total source: 6.4 GB. Total
without `.venv`, `.git`, `gdelt_events`: 215 MB (196 MB of this is the
V-Dem raw CSV).

```
   14340 .DS_Store
   18676 Aid Dependency & Reaction Dataset (1).csv
   18676 Aid Dependency & Reaction Dataset.csv
   45982 Figure_1.png
   83385 Figure_2.png
   71196 Figure_3.png
   43702 Figure_4.png
   31216 ODA Donor Dependency Analysis Sample (1).xlsx
   15513 ODA Donor Dependency Analysis Sample.xlsx
  134304 country-codes.csv
   16617 country_reaction_dataset.csv
   85494 fig1-416.png
   79225 fig2-416.png
  712598 figure_5.png
    4233 gdelt_grapher.py
    3667 gdelt_mapper.py
    2293 gdelt_scraper.py
    6610 gdelt_searcher.py
 1256185 reaction_timeline.png
    5069 reg_ready.py
      78 tempCodeRunnerFile.py
 4928709 usaid_closure_matches_rows_v1.csv
 1655274 usaid_final_geography.csv
    8196 control_regs/.DS_Store
    6148 control_regs/01_scripts/.DS_Store
    1862 control_regs/01_scripts/filter_idealpoint_columns.py
    1867 control_regs/01_scripts/filter_vdem_columns.py
    6148 control_regs/02_raw_data/.DS_Store
    5032 control_regs/02_raw_data/Codebook_IdealPointEstimates1946-2025.txt
    6148 control_regs/02_raw_data/Country_Year_V-Dem_Core_CSV_v12/.DS_Store
  105545 control_regs/02_raw_data/Country_Year_V-Dem_Core_CSV_v12/V-Dem Cautionary Notes v12.pdf
 2471388 control_regs/02_raw_data/Country_Year_V-Dem_Core_CSV_v12/V-Dem Codebook v12.pdf
  151649 control_regs/02_raw_data/Country_Year_V-Dem_Core_CSV_v12/V-Dem Suggested Citation v12.pdf
195648808 control_regs/02_raw_data/Country_Year_V-Dem_Core_CSV_v12/V-Dem-CY-Core-v12.csv
  139225 control_regs/02_raw_data/Country_Year_V-Dem_Core_CSV_v12/What's New v12.pdf
 1419867 control_regs/02_raw_data/IdealpointestimatesFP_2026FP.csv
    3972 control_regs/3-29-v2_oda_data.csv
  381869 control_regs/idealpoint_filtered.csv
   26097 control_regs/oda_controls_only.py
   18685 control_regs/produce_tables_figures.py
  835463 control_regs/vdem_filtered.csv
  (control_regs/outputs/: 4 PNG ~782 KB, 9 CSV ~3.3 KB)
       5 oda_analysis/ne_110m_admin_0_countries.cpg
  531808 oda_analysis/ne_110m_admin_0_countries.dbf
     147 oda_analysis/ne_110m_admin_0_countries.prj
   41905 oda_analysis/ne_110m_admin_0_countries.README.html
  180924 oda_analysis/ne_110m_admin_0_countries.shp
    1516 oda_analysis/ne_110m_admin_0_countries.shx
       7 oda_analysis/ne_110m_admin_0_countries.VERSION.txt
   31216 oda_analysis/ODA Donor Dependency Analysis Sample.xlsx
    7772 oda_analysis/oda_mapper.py
       2 oda_analysis/tempCodeRunnerFile.py
    6148 outputs/.DS_Store
    6148 outputs/usaid_closure_v1/.DS_Store
 4928709 outputs/usaid_closure_v1/matches_rows.csv
   52859 outputs_v3/log.txt
    1534 outputs_v3/phase1_console.txt
    6527 outputs_v3/phase1_controls_console.txt
   26187 outputs_v3/phase1_controls_run.py
   19485 outputs_v3/phase1_run.py
     426 outputs_v3/phase3_dedup_full_corpus_console.txt
    2032 outputs_v3/phase3_dedup_full_corpus.py
   26866 outputs_v3/phase3_robustness.py
    3171 outputs_v3/phase3_robustness/phase3_summary_table.csv
    2222 outputs_v3/phase3_robustness/total_articles_unique_url.csv
  (outputs_v3/phase1_controls/: 4 PNG ~826 KB, 9 CSV ~3.3 KB)
  (outputs_v3/phase1_reproduction/: 4 PNG ~860 KB, 6 CSV ~2.9 KB, 2 TXT 467 B)
    9085 outputs_v4/followup_log.txt
   13034 outputs_v4/followup_sensitivity.py
    1746 outputs_v4/followup_summary_table.csv
   12102 outputs_v4/gap_adjustment_by_country.csv
    6109 outputs_v4/log.txt
   15183 outputs_v4/sensitivity_analysis.py
    2919 outputs_v4/sensitivity_summary_table.csv
   18319 outputs_v5/analysis.py
   18504 outputs_v5/analysis2.py
   13192 outputs_v5/analysis3.py
      96 outputs_v5/domestic_outlet_counts_before_after_handcode.csv
     851 outputs_v5/domestic_outlet_counts_by_country.csv
    9380 outputs_v5/log.txt
   10960 outputs_v5/log2.txt
    7060 outputs_v5/log3.txt
     531 outputs_v5/no_article_country_profile.csv
    1561 outputs_v5/summary_table.csv
    2178 outputs_v5/summary_table2.csv
     998 outputs_v5/summary_table3.csv
    1189 outputs_v5/top50_domains_hand_coded.csv
     954 outputs_v5/top50_domains_without_country_code.csv
    4290 outputs_v5/wdi_population_gdp.csv
   68485 outputs_v6/build_all.py
    3405 outputs_v6/diff_report.txt
   17947 outputs_v6/log.txt
    3643 outputs_v6/manifest.csv
  (outputs_v6/: 8 PNG ~1.78 MB, 26 table CSV ~8.6 KB)
    6148 scatterplotting/.DS_Store
   18840 scatterplotting/3_29__oda_data.csv
   31913 scatterplotting/3_29__oda_data.xlsx
    3972 scatterplotting/3-29-v2_oda_data.csv
   19430 scatterplotting/aug_7_attempt.py
    3940 scatterplotting/confirm.py
   20015 scatterplotting/june_1_attempt.py
    5129 scatterplotting/reg_4-28.py
   20968 scatterplotting/reg_days_by_region.py
    7438 scatterplotting/reg_w_labels.py
    3854 scatterplotting/sc_plot.py
   20015 scatterplotting/tempCodeRunnerFile.py
  (scatterplotting/: 8 fig_*.png + 2 regression_*.png ~3.18 MB)
  (scatterplotting/outputs/: 4 PNG ~860 KB, 6 CSV ~2.9 KB, 2 TXT 467 B)
```
