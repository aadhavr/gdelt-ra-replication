# GDP price-base fix: final report (current-price method)

Chosen method for both Table 1 aid / GDP rows: for each country and year, gross ODA at current prices
(OECD DAC2A measure 240, price base V) divided by GDP at current prices (World Bank `NY.GDP.MKTP.CD`),
then the mean over the years 2018 to 2022 that have GDP. A missing aid year counts as 0 (same rule as
`aid_gross_2018_2022.csv`). Aid and GDP are both in current USD, so no deflator is needed.

Made by `fix_gdp/final_current_ratio.py` from files already on disk (no network call). No existing file
was edited, moved or deleted. All regressions are OLS with HC3 standard errors. s is the sample standard
deviation (ddof = 1).

## Checks (all pass; the script stops on any failure)

- Old Table 1 rows reproduce the draft: US (100, 1.16, 3.00, 0.00, 26.89), DAC (100, 2.92, 4.52, 0.03, 30.54).
- The current-price ratio reproduces cross-check 2 of the first run (`table1_old_new.csv`): max absolute
  difference 3.6e-15 (US) and 4.4e-16 (DAC), same min and max countries.
- The old G7 and B3 G8 / G9 results reproduce `gross_aid/results.csv` and `gross_aid/followup/results.csv`
  (16 rows, max absolute difference 1.1e-16, same N).
- G7 is unchanged: see section 3.

## 1. Table 1 rows

Final rows, ready to paste (percent; s = sample standard deviation, ddof = 1):

| Variable | N | Mean | s | Min | Max |
|---|---|---|---|---|---|
| Gross US ODA / GDP (%) | 100 | 1.01 | 2.61 | 0.00 | 23.40 |
| Gross DAC ODA / GDP (%) | 100 | 2.69 | 4.09 | 0.03 | 27.38 |

All versions:

| Row | Version | N | Mean | s | Min | Max | Min country | Max country |
|---|---|---|---|---|---|---|---|---|
| US ODA / GDP | old: current USD GDP | 100 | 1.16 | 3.00 | 0.00 | 26.89 | IRN | FSM |
| US ODA / GDP | first run primary: constant 2024 USD GDP, US factor | 100 | 1.00 | 2.58 | 0.00 | 23.12 | IRN | FSM |
| US ODA / GDP | **final: current aid / current GDP per year, mean** | 100 | 1.01 | 2.61 | 0.00 | 23.40 | IRN | FSM |
| DAC ODA / GDP | old: current USD GDP | 100 | 2.92 | 4.52 | 0.03 | 30.54 | KAZ | FSM |
| DAC ODA / GDP | first run primary: constant 2024 USD GDP, US factor | 100 | 2.51 | 3.88 | 0.03 | 26.25 | KAZ | FSM |
| DAC ODA / GDP | **final: current aid / current GDP per year, mean** | 100 | 2.69 | 4.09 | 0.03 | 27.38 | KAZ | FSM |

Unrounded final values: US mean 1.0061, s 2.6076, min 0.0003, max 23.4009; DAC mean 2.6941, s 4.0942,
min 0.0302, max 27.3809. SSD and ERI have no GDP (N 100 of 102).

Caveats, as in REPORT.md: YEM has GDP for 2018 only and CUB for 2018 to 2020, so their ratio uses only those
years (aid of the same years). Final values: YEM US 2.7739, DAC 6.2710; CUB US 0.0110, DAC 0.1560 (old:
YEM 4.0903 and 8.5533; CUB 0.0108 and 0.1342). Per-country values are in `ratio_changes.csv` (columns
`*_cur_pct`).

## 2. B3 models (G8 and G9 of `run_followup.py`), old vs final

Same code path (`common.gdp_models`, copied from `run_followup.py` B3), same sample (countries with
`gdp_avg > 0`, N 93 for days and 100 for attention, unchanged). Only `us_gdp` and `dac_gdp` change.
OLS, HC3 standard errors; attention beta_hat and se x 1,000.

| Model | Outcome | Term | N old / new | beta_hat old / new | HC3 se old / new | p old / new | R2 old / new |
|---|---|---|---|---|---|---|---|
| G8 aid / gdp | log(1 + days) | log us_gdp | 93 / 93 | -0.0897 / -0.0760 | 0.1217 / 0.1141 | 0.4613 / 0.5056 | 0.0144 / 0.0115 |
| G8 aid / gdp | log(1 + days) | log dac_gdp | 93 / 93 | +0.1286 / +0.1108 | 0.1969 / 0.1926 | 0.5138 / 0.5651 | 0.0144 / 0.0115 |
| G8 aid / gdp | log(1 + attention), x1000 | log us_gdp | 100 / 100 | +0.3499 / +0.3433 | 0.0871 / 0.0840 | 5.92e-05 / 4.32e-05 | 0.2668 / 0.2648 |
| G8 aid / gdp | log(1 + attention), x1000 | log dac_gdp | 100 / 100 | -0.0848 / -0.0779 | 0.1044 / 0.1015 | 0.4164 / 0.4431 | 0.2668 / 0.2648 |
| G9 ratio | log(1 + days) | log us_gdp | 93 / 93 | -0.0067 / -0.0068 | 0.0530 / 0.0534 | 0.8999 / 0.8986 | 0.0003 / 0.0003 |
| G9 ratio | log(1 + attention), x1000 | log us_gdp | 100 / 100 | +0.2969 / +0.2961 | 0.0579 / 0.0582 | 2.92e-07 / 3.65e-07 | 0.2642 / 0.2624 |
| G9 log us_share | log(1 + days) | log us_share | 93 / 93 | -0.0742 / -0.0742 | 0.1060 / 0.1060 | 0.4837 / 0.4837 | 0.0093 / 0.0093 |
| G9 log us_share | log(1 + attention), x1000 | log us_share | 100 / 100 | +0.4621 / +0.4621 | 0.1023 / 0.1023 | 6.31e-06 / 6.31e-06 | 0.1684 / 0.1684 |
| G8 levels, GDP sample | log(1 + days) | log us_gross | 93 / 93 | +0.0018 / +0.0018 | 0.0977 / 0.0977 | 0.9854 / 0.9854 | 0.2263 / 0.2263 |
| G8 levels, GDP sample | log(1 + days) | log dac_gross | 93 / 93 | -0.2969 / -0.2969 | 0.1180 / 0.1180 | 0.0119 / 0.0119 | 0.2263 / 0.2263 |
| G8 levels, GDP sample | log(1 + attention), x1000 | log us_gross | 100 / 100 | +0.4483 / +0.4483 | 0.1114 / 0.1114 | 5.69e-05 / 5.69e-05 | 0.1714 / 0.1714 |
| G8 levels, GDP sample | log(1 + attention), x1000 | log dac_gross | 100 / 100 | -0.3953 / -0.3953 | 0.1711 / 0.1711 | 0.0209 / 0.0209 | 0.1714 / 0.1714 |

B3 G8 aid / gdp, collinearity and joint HC3 Wald test that both coefficients are 0 (as in `run_followup.py`):

| Outcome | r old / new | VIF old / new | chi2(2) old / new | p old / new |
|---|---|---|---|---|
| log(1 + days) | 0.8745 / 0.8607 | 4.2512 / 3.8585 | 0.5428 / 0.4438 | 0.7623 / 0.8010 |
| log(1 + attention) | 0.8724 / 0.8606 | 4.1847 / 3.8553 | 26.3139 / 26.0202 | 1.93e-06 / 2.24e-06 |

G9 log us_share and G8 levels use GDP only to choose the sample, and the sample does not change, so they
are identical. One note: in `run_followup.py`, us_gdp / dac_gdp = us_share holds exactly. With the per-year
mean it holds only approximately (the mean of ratios is not the ratio of means), so `log us_share` is no
longer exactly log us_gdp minus log dac_gdp. G9 log us_share itself is unchanged because it uses `us_share`.

**Verdict:** no conclusion changes. Every coefficient keeps its sign, and no p-value crosses 0.05 or 0.10.
The largest change is G8 days, log dac_gdp: beta_hat +0.1286 to +0.1108 (p 0.5138 to 0.5651, not
significant either way). In the attention models, log us_gdp stays positive with p < 0.001 (G8: +0.3433,
p 4.32e-05; G9 ratio: +0.2961, p 3.65e-07) and log dac_gdp stays not significant (p 0.4431).

## 3. G7 is unchanged

G7 uses `log_gdp` = ln(`gdp_avg`) as a control, with the snapshot `gdp_avg` (current USD), and is not
changed. In the final setup all 12 G7 coefficients (aid, `log_pop`, `log_gdp`; net and gross aid; days and
attention) are bit-identical to the old run (max absolute difference 0) and match `gross_aid/results.csv`
(max absolute difference 8.3e-17). For example: G7 attention, gross, log us_gross +0.2972 (HC3 se 0.0818,
p 2.80e-04, N 100, R2 0.2674); G7 days, gross, log us_gross -0.1089 (HC3 se 0.0771, p 0.1575, N 93,
R2 0.2230). The constant-USD G7 values in REPORT.md section 4 are not used.

Table 2 columns 1 to 3 do not use GDP and are unchanged (REPORT.md section 2).

## 4. Data note

"Aid-to-GDP ratios use current-price gross ODA and current-price GDP in each year, averaged over 2018 to 2022."

## Files

New in this step: `fix_gdp/final_current_ratio.py`; `outputs/gdp_fix/table1_final.csv`, `models_final.csv`
(includes G7), `final_tables.md`, `REPORT_final.md`. Inputs used: `outputs/gdp_fix/wdi_gdp_current_2018_2022.csv`
and `oda_current_by_year.csv` (from the first run). Run from inside `fix_gdp/`.
