# Data dictionary

Every column of every input and intermediate file. "Shipped" means the
file is in the repository. Empty cells mean missing values unless stated.

---

## 1. Inputs (`data/input/`)

### 1.1 `3-29-v2_oda_data.csv` (shipped; 102 rows, one per country)
Main analysis file. No original script made it; `src/04b_merge_outcomes.py`
now rebuilds it exactly from `3_29__oda_data.csv`.

| Column | Type | Unit / meaning |
|---|---|---|
| `ISO3` | text | ISO 3166-1 alpha-3 country code |
| `country` | text | Country name |
| `us_oda_disbursements` | number stored as text | US aid, USD millions. Definition pending verification: total or average, gross or net. Egypt and Gabon have negative values. Some values have a thousands comma (for example `"2,128.8"`); scripts remove it. |
| `us_oda_loans` | number stored as text | US aid loans, USD millions, from the column `US Avg Annual ODA Loans ($M)` of the source sheet. Definition pending verification. `N/A` = missing. Not used in any regression. |
| `attention_share` | number (6 decimals) | Matched GDELT rows / all GDELT rows for the country (raw-row counts, ActionGeo country). Unitless ratio. Rounded to 6 decimals. |
| `days_to_first_article` | number | Days from 2025-01-20 to the first matched row for the country. Unit: days. Empty = no matched row (7 countries). |

### 1.2 `3_29__oda_data.csv` and `3_29__oda_data.xlsx` (shipped; source sheet)
`src/04b_merge_outcomes.py` reads the CSV; no script reads the xlsx. The CSV is an
export of the xlsx. 3 title rows, then a header row, then 143 country
rows.

Header text, quoted exactly from row 1 and row 2 of the CSV. In these quotes and in the
column names below, [U+2014] stands for an em dash in the original file:

> "ODA Dependency Analysis [U+2014] OECD DAC2A 2018–2022 (5-Year Average) + GDELT Media Dataset"

> "Sources: OECD DAC2A [U+2014] measure 206, net ODA disbursements, constant USD (2018–2022) · ODA per capita = Avg Annual ODA ÷ World Bank SP.POP.TOTL 2022 · GDELT Country Reaction Dataset"

Row 3 (group labels): "IDENTIFIER", "ODA ANALYSIS  (2018–2022 avg, OECD DAC2A)",
"GDELT MEDIA COVERAGE", "US ODA DETAIL".

To be confirmed with the data compiler.

| Column | Unit / meaning (from the column name; not verified) |
|---|---|
| `ISO3` | ISO 3166-1 alpha-3 code |
| `Country` | Country name |
| `Avg Annual ODA Received ($M)` | ODA received from all donors, USD millions (text with thousands comma) |
| `Avg Annual ODA Per Capita ($)` | USD per person (text with `$`); `N/A` = missing |
| `Top 3 Donors Combined [U+2014] Avg ($M)` | USD millions |
| `Top 3 Donors Combined (%)` | percent (text with `%`) |
| `Donor Concentration` | category: Low / Medium / High |
| `Top 3 Donors` | text, donor names separated by `|` |
| `GDELT Matched` | "✓" = in the GDELT dataset (102 rows), an em dash (U+2014) = not (41 rows) |
| `Total Articles` | GDELT rows for the country (raw-row count) |
| `USAID Articles` | matched rows for the country (raw-row count) |
| `Days Observed` | daily files with at least one row for the country |
| `Articles / Day` | Total Articles / Days Observed |
| `USAID Articles / Day` | USAID Articles / Days Observed |
| `Attention Share` | USAID Articles / Total Articles (6 decimals) |
| `Days to 1st Article` | days from 2025-01-20 |
| `US Avg Annual ODA Disbursements ($M)` | becomes `us_oda_disbursements` in 1.1 |
| `US Avg Annual ODA Loans ($M)` | becomes `us_oda_loans` in 1.1 |

### 1.3 `country-codes.csv` (shipped; 1 row per country or territory)
Country code crosswalk with UN M49 geoscheme columns. The scripts use
only these columns:

| Column | Used by | Meaning |
|---|---|---|
| `FIPS` | all mapping scripts | FIPS 10-4 code (the code GDELT 1.0 uses in `ActionGeo_CountryCode`) |
| `ISO3166-1-Alpha-3` | all mapping scripts | ISO3 code (`04_build_dataset.py` finds it as the first column whose lower-case name contains "alpha-3") |
| `Region Name`, `Sub-region Name` | `phase3_robustness.py` | UN M49 region and sub-region |

Other columns (not used): `FIFA`, `Dial`, `MARC`, `is_independent`,
`ISO3166-1-numeric`, `GAUL`, `WMO`, `ISO3166-1-Alpha-2`, `ITU`, `IOC`,
`DS`, `UNTERM Spanish Formal`, `Global Code`, `Intermediate Region Code`,
`official_name_fr`, `UNTERM French Short`, `ISO4217-currency_name`,
`UNTERM Russian Formal`, `UNTERM English Short`,
`ISO4217-currency_alphabetic_code`, `Small Island Developing States (SIDS)`,
`UNTERM Spanish Short`, `ISO4217-currency_numeric_code`,
`UNTERM Chinese Formal`, `UNTERM French Formal`, `UNTERM Russian Short`,
`M49`, `Sub-region Code`, `Region Code`, `official_name_ar`,
`ISO4217-currency_minor_unit`, `UNTERM Arabic Formal`,
`UNTERM Chinese Short`, `Land Locked Developing Countries (LLDC)`,
`Intermediate Region Name`, `official_name_es`, `UNTERM English Formal`,
`official_name_cn`, `official_name_en`, `ISO4217-currency_country_name`,
`Least Developed Countries (LDC)`, `UNTERM Arabic Short`,
`official_name_ru`, `Global Name`, `Capital`, `Continent`, `TLD`,
`Languages`, `Geoname ID`, `CLDR display name`, `EDGAR`, `wikidata_id`.

### 1.4 `wdi_population_gdp.csv` (shipped; 102 rows; frozen snapshot)
Written by `robustness/analysis.py` on 2026-10-05 from the World Bank
API. No script reads this file; the v5 scripts download WDI again.
Source: World Bank, World Development Indicators, CC BY 4.0 (see README.md).

| Column | Unit / meaning |
|---|---|
| `ISO3` | ISO3 code |
| `country` | Country name |
| `population_avg` | Mean of `SP.POP.TOTL` (total population, persons) over 2018-2022 |
| `gdp_avg` | Mean of `NY.GDP.MKTP.CD` (GDP, current US dollars) over 2018-2022. Unit: USD (not millions) |

### 1.5 `vdem_filtered.csv` (NOT shipped; make it with `src/00_filter_vdem.py`)
Country-year rows from V-Dem Country-Year Core v12. Scripts take the mean over 2018-2022.

| Column | Meaning |
|---|---|
| `country_name` | Country name |
| `country_text_id` | V-Dem country text ID (ISO3-like); used as ISO3 |
| `year` | Calendar year |
| `v2mecenefm` | V-Dem government censorship effort (media). Scale and direction: see the V-Dem Codebook v12. Scripts call it `press_censorship`. |
| `v2meharjrn` | V-Dem "Harassment of journalists". Scale and direction: see the V-Dem Codebook v12. Scripts call it `journalist_harassment`. |

### 1.6 `idealpoint_filtered.csv` (NOT shipped; make it with `src/00_filter_idealpoint.py`)
From the Voeten UNGA ideal point file. Descriptions from the dataset
codebook (`Codebook_IdealPointEstimates1946-2025.txt`).

| Column | Meaning |
|---|---|
| `iso3c` | ISO 3166-1 alpha-3 code |
| `year` | Calendar year of the UNGA session |
| `Countryname` | Country name |
| `IdealPointFP` | Posterior mean ideal point. Higher = closer to the US and Western democracies. Latent scale, about -3.59 to 3.36 |
| `NVotesFP` | Number of UNGA roll-call votes used for the estimate (count) |

The scripts compute `us_alignment` = −|mean IdealPointFP (2018-2022) −
USA mean IdealPointFP (2018-2022)|. 0 = same as the US; more negative =
further from the US.

---

## 2. Raw data (`data/raw/`, not shipped)

### 2.1 `YYYYMMDD.export.CSV.zip`
GDELT 1.0 daily Event export. One tab-separated file per zip, no header,
58 columns (see 3.1 for names). 348 files.

### 2.2 `MANIFEST.csv` (written by `src/01_download_gdelt.py`)

| Column | Unit / meaning |
|---|---|
| `file_name` | zip file name |
| `size_bytes` | file size, bytes |
| `sha256` | SHA-256 hash of the file, hex |

---

## 3. Intermediate files (`data/intermediate/`)

### 3.1 `usaid_closure_v1/matches_rows.csv` (shipped; 12,017 rows)
One row per matched GDELT event row. Written by `src/02_search.py`.
`date` + the 58 GDELT 1.0 Event columns, named `col_0` … `col_57`.
Names below follow the GDELT 1.0 Event codebook column order.

| Column | GDELT 1.0 field | Unit / meaning |
|---|---|---|
| `date` | (added by the script) | Date of the daily file, YYYYMMDD |
| `col_0` | GLOBALEVENTID | Event ID |
| `col_1` | SQLDATE | Event date, YYYYMMDD |
| `col_2` | MonthYear | YYYYMM |
| `col_3` | Year | YYYY |
| `col_4` | FractionDate | Year + fraction of year |
| `col_5`–`col_14` | Actor1Code, Actor1Name, Actor1CountryCode, Actor1KnownGroupCode, Actor1EthnicCode, Actor1Religion1Code, Actor1Religion2Code, Actor1Type1Code, Actor1Type2Code, Actor1Type3Code | CAMEO actor codes (text) |
| `col_15`–`col_24` | Actor2Code … Actor2Type3Code (same 10 fields for Actor 2) | CAMEO actor codes (text) |
| `col_25` | IsRootEvent | 0/1 |
| `col_26` | EventCode | CAMEO event code |
| `col_27` | EventBaseCode | CAMEO |
| `col_28` | EventRootCode | CAMEO |
| `col_29` | QuadClass | 1-4 |
| `col_30` | GoldsteinScale | -10 to +10 |
| `col_31` | NumMentions | count |
| `col_32` | NumSources | count |
| `col_33` | NumArticles | count |
| `col_34` | AvgTone | tone score |
| `col_35`–`col_41` | Actor1Geo_Type, Actor1Geo_FullName, Actor1Geo_CountryCode, Actor1Geo_ADM1Code, Actor1Geo_Lat, Actor1Geo_Long, Actor1Geo_FeatureID | location of Actor 1 (lat/long in degrees) |
| `col_42`–`col_48` | Actor2Geo_* (same 7 fields) | location of Actor 2 |
| `col_49`–`col_50` | ActionGeo_Type, ActionGeo_FullName | location of the event |
| `col_51` | **ActionGeo_CountryCode** | **FIPS 10-4 code of the event location. All country mapping uses this column.** |
| `col_52`–`col_55` | ActionGeo_ADM1Code, ActionGeo_Lat, ActionGeo_Long, ActionGeo_FeatureID | event location |
| `col_56` | DATEADDED | YYYYMMDD |
| `col_57` | **SOURCEURL** | **URL of the source article. Unique-URL counts use this column.** |

### 3.2 `country_reaction_dataset.csv` (shipped; 236 rows, one per ISO3)
Written by `src/04_build_dataset.py`.

| Column | Unit / meaning |
|---|---|
| `iso3` | ISO3 code (from `col_51` FIPS via `country-codes.csv`) |
| `total_articles` | All GDELT rows with this ActionGeo country, all 348 days. Count of rows (not unique URLs). |
| `usaid_articles` | Matched rows for the country. Count of rows (stored as a decimal number). |
| `days_observed` | Number of daily files with at least one row for the country. Days. |
| `total_articles_per_day` | `total_articles / days_observed`. Rows per day. |
| `usaid_articles_per_day` | `usaid_articles / days_observed`. Rows per day. |
| `attention_share` | `usaid_articles / total_articles`. Unitless ratio, unrounded. |
| `days_to_first_article` | First matched date − 2025-01-20. Days. Empty = no matched row. |

### 3.3 `total_articles_unique_url.csv` (shipped; 236 rows)
Written by `robustness/phase3_dedup_full_corpus.py`.

| Column | Unit / meaning |
|---|---|
| `ISO3` | ISO3 code |
| `total_articles_unique_url` | Number of distinct `SOURCEURL` values among all GDELT rows with this ActionGeo country, all 348 days. Count. |

### 3.4 `usaid_final_geography.csv` (NOT shipped; written by `src/03_map.py`)

| Column | Unit / meaning |
|---|---|
| `date` | Date of the daily file (YYYY-MM-DD) |
| `url` | `col_57` SOURCEURL |
| `country` | ISO 3166-1 alpha-2 code (from FIPS via the mysociety/gaze crosswalk, plus 3 manual patches) |
| `region` | `country_converter` `UNregion` name |

---

## 4. Exploratory outputs (`exploratory/tone_goldstein/`)

Made by `run_tone_goldstein.py`. Not used in the paper. The script reads
these GDELT 1.0 fields from `matches_rows.csv` (section 3.1):
`col_0` = GLOBALEVENTID, `col_30` = GoldsteinScale, `col_34` = AvgTone,
`col_51` = ActionGeo_CountryCode, `col_57` = SOURCEURL. Definitions below
follow the GDELT 1.0 event codebook.

- **AvgTone**: average tone of all documents that mention the event,
  from about -100 (very negative) to +100 (very positive); in practice
  most values are between -10 and +10. In the 12,017 matched rows it is
  -16.7 to +7.0. Unitless score.
- **GoldsteinScale**: the theoretical effect of this type of event on
  the stability of a country, -10 (most conflictual) to +10 (most
  cooperative). It depends on the event code only. Unitless score.

### 4.1 `results.csv` (12 rows: 2 outcomes x 6 models)

| Column | Unit / meaning |
|---|---|
| `outcome` | `avgtone` or `goldstein` |
| `model` | m1 to m5, or the event-level robustness row (see README.md, section 8) |
| `N` | number of countries (m1 to m4, event level) or of country-url pairs (m5) |
| `beta_hat` | coefficient on log aid (score points per one unit of log aid) |
| `se_type` | `HC3`, or `cluster by country (93)` for m5 |
| `se` | standard error of `beta_hat`, same unit |
| `p` | two-sided p-value of `beta_hat` |
| `r2` | R-squared (weighted R-squared for the WLS model m3) |

### 4.2 `descriptives.csv`

| Column | Unit / meaning |
|---|---|
| `measure` | which variable: avgtone or goldstein (country mean over urls, or over events), or `n_urls` (analysis sample, or all 102 countries with 0 for none) |
| `N` | number of countries |
| `mean`, `sd`, `min`, `max` | mean, standard deviation (ddof = 1), minimum and maximum, in the unit of the measure |
| `p25`, `median`, `p75` | quartiles (only for `n_urls`) |
| `n_lt_5`, `n_ge_5` | countries with fewer than 5 / at least 5 matched urls (only for `n_urls`) |

---

## 5. Exploratory: press freedom (`exploratory/press_freedom/results.csv`)

Same columns as section 4.1 (`outcome, model, N, beta_hat, se_type, se,
p, r2`). Each model gives 4 rows, named in `model`:
- `aid at mean moderator`: coefficient on log aid (the moderator is
  centered, so this is the aid effect at average press freedom);
- `aid x moderator`: the interaction coefficient;
- `aid slope at moderator p10` / `p90`: the aid effect at the 10th / 90th
  percentile of the moderator, with `se_type` `HC3 (t, df resid)` (same
  method as Table 9).
For the attention outcome, `beta_hat` and `se` are per 1,000. `r2` is
the R-squared of the model (the same on its 4 rows). The moderators are
`v2mecenefm` and `v2meharjrn` (section 1.5): a high value means less
censorship and less harassment.

## 6. Exploratory: coverage intensity (`exploratory/coverage_intensity/results.csv`)

Same columns as section 4.1. `outcome` is the natural log of a
country's mean of one field (mean over its unique country-URL pairs).

| Field | Column in `matches_rows.csv` | Meaning (from the field name; the codebook is not in the project) |
|---|---|---|
| NumMentions | `col_31` | count of mentions of the event (count) |
| NumSources | `col_32` | count of information sources that mention the event (count) |
| NumArticles | `col_33` | count of source documents that mention the event (count) |

These are **event-level** counts (one value per GDELT event row), not
counts for one article. The GDELT 1.0 codebook is not in this project,
so the time window that these counts cover is not confirmed here. In the
11,833 matched rows with a country, the medians are 5, 1 and 5 and the
maximums are 3,118, 343 and 3,118 (skewness 18.2, 12.0 and 18.3).

## 7. Exploratory: US-specific aid dependency (`exploratory/us_specific_aid/`)

Made by `run_us_specific_aid.py`. Specification: see the README.md in
that folder. Explanatory variables (natural logs; values <= 0 are dropped):

| Variable | Definition |
|---|---|
| `log_us_gdp` | log(US aid ÷ GDP): `us_oda_disbursements` (USD millions, section 1.1) × 1,000,000 ÷ `gdp_avg` (USD, section 1.4) |
| `log_oda_gdp` | log(total ODA ÷ GDP): `Avg Annual ODA Received ($M)` (section 1.2) × 1,000,000 ÷ `gdp_avg` |
| `log_us_oda_share` | log(US aid ÷ total ODA) |
| `log_us_aid` | log(US aid, USD millions) |

### 7.1 `us_specific_results.csv` (16 rows: one per model and variable)

| Column | Unit / meaning |
|---|---|
| `model` | model label; rows starting `Restricted >=5 matched EVENT ROWS` use only countries with `usaid_articles` >= 5 |
| `n` | number of countries (98 full sample, 78 restricted) |
| `variable` | explanatory variable (the intercept is not reported) |
| `beta` | negative-binomial GLM coefficient (alpha fixed at 1, offset log `total_articles`): change in log expected matched rows per one unit of the log variable |
| `se` | HC3 standard error of `beta` |
| `p` | two-sided p-value (normal) |
| `ci_low`, `ci_high` | 95% confidence interval of `beta` |
| `aic` | AIC of the model (the same on all its rows) |

### 7.2 `analysis_sample.csv` (98 rows: the complete-case sample)

`ISO3`; `usaid_articles` and `total_articles` (GDELT row counts from
section 3.2); `log_volume` = log `total_articles` (the offset); and the
four log variables above.

### 7.3 `checks_results.csv` (made by `run_us_specific_aid_checks.py`)

Same columns as section 7.1, plus:

| Column | Unit / meaning |
|---|---|
| `count_type` | `event rows` (outcome `usaid_articles`, offset log `total_articles`) or `unique urls` (outcome = unique matched URLs, offset log `total_articles_unique_url`) |
| `aid_values` | `as published (drop nonpositive)` or `bottom-coded US aid` (US aid <= 0 set to the smallest positive value in the sample, 0.7 USD millions) |

Restricted rows use >= 5 of the `count_type` (event rows or unique URLs).

### 7.4 `checks_collinearity.csv`

| Column | Unit / meaning |
|---|---|
| `count_type`, `aid_values` | as in section 7.3 |
| `sample` | `full`, or the >= 5 restricted sample |
| `n` | number of countries |
| `pearson_r`, `spearman_rho` | correlation of `log_us_gdp` and `log_oda_gdp` in that sample |
| `vif` | 1 / (1 - `pearson_r`^2), the VIF of either variable in the two-variable model |
| `joint_wald_chi2`, `joint_wald_df`, `joint_wald_p` | HC3 Wald test that both coefficients are 0 in the model `US aid/GDP + total ODA/GDP` (chi-squared, 2 df) |

### 7.5 `checks_negative_aid.csv` (the 4 countries outside the 98-country sample)

`ISO3`; `us_aid_m` (US net ODA, USD millions); `us_loans_m` (`US Avg Annual
ODA Loans ($M)` from the source sheet); `total_oda_m` (USD millions);
`gdp_avg` (USD); the ratios `us_gdp`, `oda_gdp`, `us_oda_share` before logs;
`usaid_articles` (event rows); `usaid_articles_unique` (unique URLs);
`reason` (why the country is excluded).

