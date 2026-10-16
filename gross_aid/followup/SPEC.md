# spec: gross aid follow-up checks (written before any model was run)

## general rules

- all models use the same logs, the same hc3 standard errors and the same
  sample rules as `gross_aid/SPEC.md` unless stated here. the regressor is
  the natural log of the aid variable; a value <= 0 gives a missing log and
  the country leaves that model. ols with hc3 for every model below.
- outcomes: days = log(1 + days to first article); attention =
  log(1 + unique-url attention share), beta-hat and se shown per 1,000.
- the analysis file, `usaid_articles_unique`, the outcomes and the gross aid
  columns are built with lines copied from `gross_aid/run_gross_aid.py`.
- models: g1 (days ~ log us_gross), g2 (attention ~ log us_gross), g8 (outcome
  ~ log us_gross + log dac_gross, for days and for attention, with pearson r
  of the two logs, vif = 1 / (1 - r^2) and an hc3 wald test that both
  coefficients are 0), g9 (outcome ~ log us_share, for days and for
  attention).
- no step is random. a fixed seed (0) is set anyway.
- no statement that a result supports or rejects salience or dampening.

## check before any new model

reproduce these full-sample gross values of `gross_aid/results.csv` and stop
if one does not match at the precision shown: g1 -0.16708 (n 95), g2 0.21245
(n 102), g8 days us 0.0054 and dac -0.2968, g8 attention us 0.4321 and dac
-0.3871, g9 days -0.0958, g9 attention 0.4473.

## part a (read-only, no models)

- a1: column names of `data/raw/oecd_gross_us_2018_2022.csv`; values of
  `OBS_STATUS` for irn, eri and the whole file.
- a2: for irn and eri, the years and values in the us file and in the dac
  file.
- a3: for irn and eri, us_gross_mean (sum / 5), sum / n_years, and
  `us_oda_disbursements` of the net sheet; which of the first two is closer
  to the net value. no claim that a missing year is a true zero.

## b1: restriction on matched articles

- keep countries with `usaid_articles_unique` >= 5 (matched unique urls).
  primary threshold 5, second threshold 10.
- gross aid only: g1, g2, g8 (both outcomes), g9 (both outcomes).
- the full-sample row is shown next to each restricted row. n is reported
  and the countries dropped at each threshold are listed (from the
  102-country analysis file, with their count).
- the restriction uses the same count that builds the attention outcome
  (`usaid_articles_unique` is the numerator of the attention share), so it
  selects on the outcome.

## b2: iran and eritrea

irn has 2 and eri has 3 years of us data in the us file. g1, g2, g8, g9 in
two variants, each next to the full-sample row:

- (i) drop irn and eri.
- (ii) keep them, but for these two use sum / n_years_us as us_gross_mean
  (sum from the raw us file), and recompute us_share = that value /
  dac_gross_mean. all other countries unchanged.

## b3: aid over gdp (extra, not in the original spec)

- `gdp_avg` in `data/input/wdi_population_gdp.csv` is the 2018-2022 mean of
  wdi `NY.GDP.MKTP.CD`, gdp in current us dollars, unit usd (not millions)
  (DATA_DICTIONARY.md section 1.4, README.md). the aid columns are usd
  millions. so: us_gdp = us_gross_mean x 1,000,000 / gdp_avg and dac_gdp =
  dac_gross_mean x 1,000,000 / gdp_avg.
- the price bases differ: aid is constant 2024 prices, gdp is current
  prices (mean over 2018-2022). the ratio mixes the two. this is reported,
  not corrected.
- gdp_avg is missing for 2 countries, so n falls; n is reported.
- g8 with log us_gdp + log dac_gdp, both outcomes, with r, vif and the wald
  test.
- g9: us_gdp / dac_gdp = us_share, so g9 with the two ratios is the same
  regressor as g9. it is run on the countries with gdp_avg (sample change
  only). in addition, labelled "g9 ratio": outcome ~ log us_gdp alone.
- to separate the sample change from the ratio, g8 with the levels (log
  us_gross + log dac_gross) is also run on the countries with gdp_avg.

## outputs

- `gross_aid/followup/results.csv`: model, variant, outcome, n, beta_hat,
  se, p, r2, note. g8 has one row per coefficient; r, vif and the wald test
  go in the note of the g8 rows.
- `gross_aid/followup/log.txt`: part a output, the check, and all models.
