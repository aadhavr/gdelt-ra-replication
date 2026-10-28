# Where gdp_avg is used

`gdp_avg` is the 2018-2022 mean of WDI `NY.GDP.MKTP.CD`, GDP in current US dollars, unit USD
(DATA_DICTIONARY.md section 1.4). The gross aid columns `us_gross_mean` and `dac_gross_mean` are OECD
DAC2A measure 240, constant 2024 USD millions (section 8.2). Found with
`grep -rn --include='*.py' -iE 'gdp|NY\.GDP|WDI_SNAPSHOT|wdi_population' .` (the .venv folder left out).
No file in `src/`, `robustness/build_all.py`, `robustness/oda_controls_only.py` or the sensitivity scripts
mentions GDP.

## In scope (rerun in fix_gdp/)

| Script | Lines | Use | Output |
|---|---|---|---|
| `gross_aid/share_main/run_share_main.py` | 23, 125-126 | reads `gdp_avg` from the snapshot | |
| | 131-133 | `us_gdp = us_gross_mean x 1e6 / gdp_avg`, `dac_gdp = dac_gross_mean x 1e6 / gdp_avg` (aid in constant 2024 USD over GDP in current USD) | |
| | 66-67, 258-282 | Table 1 rows "gross us oda / gdp, percent" and "gross dac oda / gdp, percent" | `gross_aid/share_main/table1_check.csv` rows 7 and 8 |
| | 260-262 | prints the countries with no `gdp_avg` | `log.txt` |
| `gross_aid/followup/run_followup.py` | 97-98 | reads `gdp_avg` | |
| | 255-274 | B3: sample `gdp_avg > 0` (N 100 of 102); `us_gdp`, `dac_gdp` as above; G8 levels on the GDP sample, G8 log us_gdp + log dac_gdp, G9 log us_share on the GDP sample, G9 ratio log us_gdp | `gross_aid/followup/results.csv`, variants starting "B3" (12 rows) |
| `gross_aid/run_gross_aid.py` | 91-96 | reads `population_avg` and `gdp_avg`; `log_gdp = ln(gdp_avg)` | |
| | 194, 204-205 | G7 days and G7 attention: aid + `log_pop` + `log_gdp`, net and gross aid | `gross_aid/results.csv` rows "G7 days", "G7 attention" (4 rows) |

`run_gross_aid.py` G8 (joint, line 207-220) and G9 (line 222-224) do not use GDP: their regressors are
`log_us_gross`, `log_dac_gross` and `log_us_share` only, on the full 102-country file. The G8 and G9 that use
GDP are the B3 versions in `run_followup.py`.

## Table 2 columns 1 to 3 do not use GDP

In `run_share_main.py` the regressors are built at lines 128-130 from `us_share` (S), `dac_gross_mean` (T),
`us_gross_mean` (U) and `total_articles_unique_url` (V). The model formulas are
`MODELS = {"M1": ["S"], "M2": ["S", "T"], "M3": ["U", "T"], "M4": ["U"]}` (line 41), turned into
`f"{y} ~ {' + '.join(xs)}"` at line 142. Draft Table 2 maps (1) to M4 (U), (2) to M1 (S) and (3) to M2 (S + T)
(lines 390-392). `gdp_avg`, `us_gdp` and `dac_gdp` appear in no formula; after `load()` they are used only by
`table1()` (lines 260-262 and the two TABLE1 rows). The Table 2 samples (full, matched urls >= 5, >= 10, drop
IRN ERI) do not filter on GDP (lines 447-449). So Table 2 columns 1 to 3 do not depend on GDP.

## Out of scope (listed only, not rerun)

| Script | Lines | Use |
|---|---|---|
| `exploratory/us_specific_aid/run_us_specific_aid.py` | 52-62, 20-26 | `us_gdp = us_aid_m x 1e6 / gdp_avg`, `oda_gdp = total_oda_m x 1e6 / gdp_avg` from the snapshot; negative binomial models with log US aid/GDP and log total ODA/GDP. The numerators are net aid (price base not known), so the price base issue here is a separate one |
| `exploratory/us_specific_aid/run_us_specific_aid_checks.py` | 62-65, 83-86, 118-130, 159-177 | same ratios; collinearity, Wald test, the list of countries with no `gdp_avg` |
| `robustness/analysis.py` | 189-260 | downloads `NY.GDP.MKTP.CD` live from api.worldbank.org; `log_gdp` control with net aid (OLS HC3 and Cox); wrote the `wdi_population_gdp.csv` snapshot (244-245) |
| `robustness/analysis2.py` | 114-121, 199-237 | live WDI download; `log_gdp` control in Cox and OLS with imputed days |
| `robustness/analysis3.py` | 93-98, 117-123, 147-250 | live WDI download; `log_gdp` control in OLS and Cox |
| `robustness/phase3_robustness.py` | 11, 373-379 | text only: says GDP is not used |

The `log_gdp` controls (G7 and the robustness scripts) are less exposed than the ratios: a multiplier common
to all countries and years only shifts the intercept. A conversion that differs by year (f_t) changes
ln(mean_t GDP_t x f_t) - ln(mean_t GDP_t) a little from country to country, so the coefficients can still move.
