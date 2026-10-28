# GDP price-base fix: report

Made by the scripts in `fix_gdp/`. No existing file was edited, moved or deleted; the paper was not edited.
All regressions are OLS with HC3 standard errors. s is the sample standard deviation (ddof = 1).

## 1. The mismatch

`gdp_avg` is the 2018-2022 mean of World Bank `NY.GDP.MKTP.CD`, GDP in **current** US dollars. Gross ODA
(`us_gross_mean`, `dac_gross_mean`) is OECD DAC2A measure 240 in **constant 2024** US dollars. Dividing one by
the other mixes the two price bases. Because 2018-2022 dollars are worth more in 2024 dollars (the US factor
Q / V is 1.06 to 1.23), the old ratios overstate aid / GDP by about 12 to 18 percent.

The fix converts GDP to constant 2024 USD with the OECD's own factor. For each year t,
f_t = Q_t / V_t is US gross ODA to developing countries (recipient `DPGC`) at constant 2024 prices (Q)
over the same at current prices (V). GDP_const,t = GDP_current,t x f_t and `gdp_const_avg` is the mean
over the years with GDP. The ratio stays (aid 5-year mean) / `gdp_const_avg`.

| year | f_t, US | f_t, DAC total |
|---|---|---|
| 2018 | 1.2262 | 1.1146 |
| 2019 | 1.2063 | 1.1277 |
| 2020 | 1.1903 | 1.0936 |
| 2021 | 1.1383 | 1.0343 |
| 2022 | 1.0627 | 1.0687 |

The US Q / V is almost the same for every recipient (the widest spread over recipients is 1.0611 to 1.0628,
in 2022), so it is the US deflator. The DAC-total Q / V varies a lot by recipient (0.78 to 1.25), because
each recipient has a different mix of donors.

### Data checks

- **OECD pull.** One SDMX call to `sdmx.oecd.org` (URL and time in
  `data/raw_oecd_pull/dac2a_usa_dac_240_QV_2018_2022.query.txt`), HTTP 200, no error, no retry. Q base period
  2024, flow type D, measure 240, USD millions.
- **Q pull vs `us_gross_mean`.** All 505 US (and 510 DAC) country-year Q values of the 102 sample countries are
  bit-identical to `data/raw/oecd_gross_us_2018_2022.csv` (and the DAC file). The 5-year means are exactly
  equal for 87 of 102 countries and differ by at most 5.7e-14 for the rest (DAC: 94 of 102, at most 2.3e-13).
  This is float summation order, not data: summing the original `data/raw` file the same way also matches
  only 87 of 102. A first run that asked for bit-equal means stopped (record in `pull_check.csv`); the run used
  for this report checks the yearly values bit for bit and the means to 1e-12 (`pull_check_yearly.csv`). The
  aid numerators used everywhere are still the unchanged `aid_gross_2018_2022.csv`; the pull is used only
  for f_t and for cross-check 2.
- **World Bank GDP.** The new download (data last updated 2026-10-08) gives 5-year means equal to the
  snapshot `gdp_avg` for all 100 countries that have one (largest relative difference 2.2e-16).
- **Missing GDP.** SSD and ERI have no GDP in any year (N 100 of 102, as before).
- **Caveats: YEM and CUB.** YEM has GDP for 2018 only, CUB for 2018 to 2020. Their `gdp_const_avg` uses
  only those years, but the aid numerator is still the 5-year mean. So their relative change is larger than
  for the 98 five-year countries (-12.0% to -15.6%), because the early years have the largest f_t:

| ISO3 | GDP years | row | old % | new % | relative change | DAC factor % | current-price route % |
|---|---|---|---|---|---|---|---|
| YEM | 1 (2018) | US | 4.0903 | 3.3358 | -18.4% | 3.6696 | 2.7739 |
| YEM | 1 (2018) | DAC | 8.5533 | 6.9755 | -18.4% | 7.6736 | 6.2710 |
| CUB | 3 (2018-2020) | US | 0.0108 | 0.0090 | -17.2% | 0.0097 | 0.0110 |
| CUB | 3 (2018-2020) | DAC | 0.1342 | 0.1112 | -17.2% | 0.1208 | 0.1560 |

## 2. Usage map (full version: `usage_map.md`)

| Where | GDP use | Affected output |
|---|---|---|
| `gross_aid/share_main/run_share_main.py` 125-133, 258-282 | `us_gdp`, `dac_gdp` = aid x 1e6 / `gdp_avg` | Table 1 rows "gross us oda / gdp" and "gross dac oda / gdp" |
| `gross_aid/followup/run_followup.py` 255-274 | B3: sample `gdp_avg > 0`; G8 with log us_gdp + log dac_gdp; G9 ratio log us_gdp; G8 levels and G9 log us_share on the GDP sample (sample only) | B3 rows of `gross_aid/followup/results.csv` |
| `gross_aid/run_gross_aid.py` 91-96, 194, 204-205 | `log_gdp` as a control in G7 | G7 days, G7 attention (net and gross aid) |

Only the B3 versions of G8 and G9 use GDP. G8 and G9 in `run_gross_aid.py` do not. Listed but not rerun:
`exploratory/us_specific_aid/run_us_specific_aid.py` and `run_us_specific_aid_checks.py` (net aid / GDP;
the net aid price base is not known), `robustness/analysis.py`, `analysis2.py`, `analysis3.py` (`log_gdp`
control with net aid, live WDI download).

**Table 2 columns 1 to 3 are unchanged.** They are M4 (ln U), M1 (ln S) and M2 (ln S + ln T) of
`run_share_main.py` (lines 390-392). The formulas use only S = ln(us_share), T = ln(dac_gross_mean) and
U = ln(us_gross_mean) (`MODELS`, line 41; regressors built at lines 128-130). `gdp_avg`, `us_gdp` and
`dac_gdp` enter no formula, and no Table 2 sample filters on GDP. So the fix cannot change Table 2.

## 3. Table 1 rows, old vs new (ready to paste)

Percent. s = sample standard deviation (ddof = 1). GDP in constant 2024 USD (US factor).

| Variable | N | Mean | s | Min | Max |
|---|---|---|---|---|---|
| Gross US ODA / GDP (%) | 100 | 1.00 | 2.58 | 0.00 | 23.12 |
| Gross DAC ODA / GDP (%) | 100 | 2.51 | 3.88 | 0.03 | 26.25 |

Old (current USD GDP), for comparison:

| Variable | N | Mean | s | Min | Max |
|---|---|---|---|---|---|
| Gross US ODA / GDP (%) | 100 | 1.16 | 3.00 | 0.00 | 26.89 |
| Gross DAC ODA / GDP (%) | 100 | 2.92 | 4.52 | 0.03 | 30.54 |

Min and max countries do not change: US row min IRN, max FSM; DAC row min KAZ, max FSM. Unrounded new
values: US mean 0.9964, s 2.5755, min 0.0004, max 23.1157; DAC mean 2.5107, s 3.8770, min 0.0294,
max 26.2517.

10 largest changes (percentage points):

| ISO3 | US old % | US new % | change pp | | ISO3 | DAC old % | DAC new % | change pp |
|---|---|---|---|---|---|---|---|---|
| FSM | 26.894 | 23.116 | -3.778 | | FSM | 30.542 | 26.252 | -4.291 |
| AFG | 8.374 | 7.150 | -1.223 | | AFG | 18.985 | 16.211 | -2.774 |
| SOM | 6.590 | 5.683 | -0.907 | | SOM | 18.321 | 15.798 | -2.522 |
| LBR | 5.839 | 5.031 | -0.808 | | CAF | 14.630 | 12.581 | -2.050 |
| CAF | 5.521 | 4.747 | -0.773 | | SYR | 13.578 | 11.683 | -1.896 |
| YEM | 4.090 | 3.336 | -0.755 | | YEM | 8.553 | 6.976 | -1.578 |
| SYR | 4.224 | 3.634 | -0.590 | | LBR | 9.392 | 8.092 | -1.300 |
| LSO | 3.770 | 3.236 | -0.534 | | VUT | 9.165 | 7.884 | -1.280 |
| MOZ | 3.648 | 3.146 | -0.502 | | MOZ | 8.758 | 7.554 | -1.204 |
| MWI | 3.341 | 2.878 | -0.463 | | TLS | 7.571 | 6.584 | -0.986 |

The relative change is -12.0% to -15.6% for the 98 countries with 5 GDP years, so the countries with the
largest ratios have the largest absolute changes. Every country is in `ratio_changes.csv`.

## 4. Models that use GDP, old vs new

OLS, HC3 standard errors; attention beta_hat and se x 1,000. Same code, same samples, only GDP changed.
N is the same in every model. The full table with all 24 coefficients (including `log_pop`) is in
`report_tables.md` and `models_old_new.csv`.

| Model | Outcome | Term | N | beta_hat old / new | HC3 se old / new | p old / new | R2 old / new |
|---|---|---|---|---|---|---|---|
| G7 net | days | log net aid | 91 | -0.1146 / -0.1144 | 0.0818 / 0.0818 | 0.1613 / 0.1616 | 0.2176 / 0.2175 |
| G7 net | days | log_gdp | 91 | -0.0644 / -0.0639 | 0.1014 / 0.1012 | 0.5257 / 0.5278 | |
| G7 net | attention | log net aid | 98 | +0.3075 / +0.3076 | 0.0834 / 0.0834 | 2.25e-04 / 2.24e-04 | 0.2708 / 0.2711 |
| G7 net | attention | log_gdp | 98 | -0.3166 / -0.3171 | 0.1263 / 0.1263 | 0.0122 / 0.0121 | |
| G7 gross | days | log us_gross | 93 | -0.1089 / -0.1088 | 0.0771 / 0.0770 | 0.1575 / 0.1580 | 0.2230 / 0.2229 |
| G7 gross | days | log_gdp | 93 | -0.0721 / -0.0715 | 0.1004 / 0.1002 | 0.4728 / 0.4753 | |
| G7 gross | attention | log us_gross | 100 | +0.2972 / +0.2973 | 0.0818 / 0.0818 | 2.80e-04 / 2.78e-04 | 0.2674 / 0.2677 |
| G7 gross | attention | log_gdp | 100 | -0.3178 / -0.3182 | 0.1261 / 0.1261 | 0.0118 / 0.0116 | |
| B3 G8 aid / gdp | days | log us_gdp | 93 | -0.0897 / -0.0896 | 0.1217 / 0.1217 | 0.4613 / 0.4615 | 0.0144 / 0.0144 |
| B3 G8 aid / gdp | days | log dac_gdp | 93 | +0.1286 / +0.1285 | 0.1969 / 0.1969 | 0.5138 / 0.5141 | |
| B3 G8 aid / gdp | attention | log us_gdp | 100 | +0.3499 / +0.3498 | 0.0871 / 0.0871 | 5.92e-05 / 5.93e-05 | 0.2668 / 0.2670 |
| B3 G8 aid / gdp | attention | log dac_gdp | 100 | -0.0848 / -0.0844 | 0.1044 / 0.1044 | 0.4164 / 0.4189 | |
| B3 G9 ratio | days | log us_gdp | 93 | -0.0067 / -0.0067 | 0.0530 / 0.0530 | 0.8999 / 0.8993 | 0.0003 / 0.0003 |
| B3 G9 ratio | attention | log us_gdp | 100 | +0.2969 / +0.2970 | 0.0579 / 0.0579 | 2.92e-07 / 2.89e-07 | 0.2642 / 0.2644 |

B3 "G8 levels on the GDP sample" and "G9 log us_share" use GDP only to pick the sample (N 93 and 100), and
the sample does not change, so they are identical old and new (G8 levels attention: +0.4483 and -0.3953;
G9 log us_share attention: +0.4621, p 6.31e-06).

Across all 24 coefficients: the largest change in beta_hat is 0.00056 (log_pop in G7 days, gross), the
largest change in p is 0.0043 (same term), the largest change in an HC3 se is 0.00022 and in R2 0.00024.
No sign changes, and no p-value crosses 0.05 or 0.10.

Why so small: in the logs, a constant multiplier on GDP only shifts the intercept. The new GDP is old GDP
times a GDP-weighted mean of f_t, which is 1.137 to 1.226 and nearly the same for most countries.

Verdicts:
- **G7 (log_gdp control), net and gross, days and attention:** no conclusion changes.
- **B3 G8 (log us_gdp + log dac_gdp):** no conclusion changes.
- **B3 G9 ratio (log us_gdp) and B3 G9 log us_share:** no conclusion changes (G9 log us_share is identical).
- **Table 2 columns 1 to 3:** unchanged by construction (section 2).
- **Table 1 aid / GDP rows:** these change: means fall by 14% (US 1.16 to 1.00, DAC 2.92 to 2.51).

## 5. Cross-checks

**Cross-check 1 (DAC-total factor).** Using f_t of DAC total ODA to developing countries instead of the US
factor gives US 1.07 (s 2.76, max 24.73) and DAC 2.69 (s 4.15, max 28.08). Each country's ratio is 5.4% to
10.0% (median 6.9%) higher than with the US factor. This is the DAC row moving from 2.51 to 2.69.

**Cross-check 2 (no deflator).** Gross ODA at current prices (V) / current GDP, year by year, averaged
over the years with GDP (a missing aid year counts as 0):

| Row | primary (US factor) | DAC factor | current-price route |
|---|---|---|---|
| US ODA / GDP, mean (s) | 1.00 (2.58) | 1.07 (2.76) | 1.01 (2.61) |
| DAC ODA / GDP, mean (s) | 2.51 (3.88) | 2.69 (4.15) | 2.69 (4.09) |

- **US row:** close to the primary. Per country, the median relative difference is +0.4% (median absolute
  0.8%), and 75% of countries are within 2%. The largest gaps are not from the deflator but from the
  ratio-of-means vs mean-of-ratios difference where GDP moved a lot (LBN +25%, its GDP fell from 54.9 to
  21.0 billion USD; VEN +20%), or where aid and GDP cover different years (YEM -17%: one GDP year against
  a 5-year aid mean). Log correlation with the primary: r = 0.9997.
- **DAC row:** the current-price route is closer to the **DAC factor** (median relative difference +0.7%)
  than to the US factor (+7.6%). DAC constant-price ODA is built with each donor's own deflator, so the US
  factor does not match it. The numbers suggest the DAC factor is the better choice for the DAC row; the
  choice is yours. The models in section 4 were run with the US factor only; they were not rerun with the
  DAC factor.

## 6. Suggested note for the Data section

"Because OECD aid figures are in constant 2024 US dollars, we convert World Bank GDP (current US dollars,
NY.GDP.MKTP.CD) to constant 2024 dollars year by year with the OECD's own conversion factor (the ratio of
US gross ODA disbursements at constant 2024 and at current prices, DAC2A), before taking the 2018-2022 mean."

If you use the DAC factor for the DAC row, change "US gross ODA" to "US gross ODA for the US aid ratio and
DAC total gross ODA for the DAC aid ratio".

## Files

Code: `fix_gdp/common.py`, `reproduce_current.py`, `fetch_wdi_gdp.py`, `pull_oecd.py`,
`build_gdp_constant.py`, `compare_old_new.py`, `report_tables.py`.
Raw pull: `data/raw_oecd_pull/dac2a_usa_dac_240_QV_2018_2022.csv` and `.query.txt`.
Outputs in `outputs/gdp_fix/`: `usage_map.md`, `reproduce_current.csv`, `wdi_gdp_current_2018_2022.csv`,
`pull_check.csv` (strict first run, stopped), `pull_check_yearly.csv`, `conversion_factors.csv`,
`gdp_constant_2024.csv`, `oda_current_by_year.csv`, `table1_old_new.csv`, `ratio_changes.csv`,
`models_old_new.csv`, `crosscheck.csv`, `report_tables.md`, `REPORT.md`.

Run from inside `fix_gdp/` (the scripts import `common.py`), in this order: `reproduce_current.py`, `fetch_wdi_gdp.py`, `pull_oecd.py`,
`build_gdp_constant.py`, `compare_old_new.py`, `report_tables.py` (each stops if its output exists).
