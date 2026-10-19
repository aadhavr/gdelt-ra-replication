revised after the first run to remove models that were not requested by the co-author; original sha-256 50ed8c2832a7f5ba14d3e931f2ee5db95bf4bad50e2c73673ff58372aee985fa.

# spec: us share of gross dac aid as the central regressor, untransformed attention share as the main outcome (written before any model or statistic was run)

## what the outcome measures

the attention outcome is international news attention associated with a
country's event geography. gdelt assigns each event to a country by the
location of the event (`ActionGeo_CountryCode`, `col_51` of the matched
rows), not by the location of the outlet. the outcome is not coverage
produced by domestic media outlets of that country.

## general rules

- same analysis file, aid columns, logs and sample rules as
  `gross_aid/SPEC.md` and `gross_aid/followup/SPEC.md`. lines are copied
  from `gross_aid/run_gross_aid.py` and `gross_aid/followup/run_followup.py`;
  those scripts are not imported or edited.
- a value <= 0 gives a missing log, and the country leaves that model.
- every step is deterministic. a fixed seed (0) is set anyway.
- no statement that a result supports or rejects salience or dampening.

## outcomes

- attention, main: untransformed attention share from unique urls,
  `attention_share_unique` = `usaid_articles_unique` /
  `total_articles_unique_url` (a fraction, not a percent).
- attention, robustness: ln(1 + `attention_share_unique`), as in Table 4.
- for both attention outcomes, beta-hat and se are reported times 1,000.
- days: ln(1 + days to first article), unchanged, not scaled.

## regressors

gross oda, oecd dac2a measure 240, disbursements, constant 2024 usd
millions, 2018-2022 mean (sum / 5, a missing year counts as 0), same rules
as `gross_aid/SPEC.md`.

- us_share = `us_gross_mean` / `dac_gross_mean`.
- S = ln(us_share).
- T = ln(`dac_gross_mean`) (total dac gross aid, usd millions, levels).
- U = ln(`us_gross_mean`).

## models

attention means both attention outcomes: raw (main) and ln(1 + share)
(robustness).

- M1: outcome ~ S (central model), for attention and for days (the
  draft's timing number).
- M2: outcome ~ S + T (donor concentration controlling for total dac aid),
  attention only.
- M3: outcome ~ U + T (the old joint model G8), attention only, used only
  to check the equivalence below.
- M4: outcome ~ U (single us aid, draft table 2 column 1), attention only.

count: M1 x 3 outcomes + M2, M3, M4 x 2 outcomes = 9 ols models on the
full sample.

## standard errors

- hc3 for all ols models.
- negative binomial: model-based se, as G6 in
  `gross_aid/run_gross_aid.py`.
- r2 for ols only.

## robustness samples (M1 and M2 only, attention outcomes only)

- (a) `usaid_articles_unique` >= 5.
- (b) `usaid_articles_unique` >= 10.
- (c) drop IRN and ERI (IRN has 2 and ERI has 3 years of us data).

same definitions as `gross_aid/followup/SPEC.md`. (a) and (b) use the same
count that builds the attention outcome (`usaid_articles_unique` is the
numerator of the share), so they select on the outcome. the countries
dropped in each sample are listed.

count: 2 models x 2 outcomes x 3 samples = 12 ols models.

## count models (regressors S, and S + T)

- negative binomial glm (alpha 1, as G6): `usaid_articles_unique` ~ S, and
  ~ S + T, offset ln(`total_articles_unique_url`).

count: 2 negative binomial models.

## equivalence claims to verify (each attention outcome)

S = U - T, so M2 is a reparametrisation of M3. checks:

1. M2 and M3 have the same fitted values (max abs difference) and the same
   r2.
2. coef on S in M2 = coef on U in M3.
3. coef on T in M2 = coef on U + coef on T in M3.
4. hc3 se of T in M2 = sqrt(v_U + v_T + 2 cov_UT), from the hc3 covariance
   of M3.

a check passes if the max abs difference is below 1e-8 (on the unscaled
coefficients).

## collinearity (full sample, pairwise complete)

- pearson corr(S, T) and its vif = 1 / (1 - r^2).
- pearson corr(U, T) and its vif.

## pre-check (before any new model)

reproduce, from the log versions, at 4 decimals, and stop if one does not
match: G9 days -0.0958 (N 95), G9 attention 0.4473 (N 102), G8 days US
0.0054 and DAC -0.2968, G8 attention US 0.4321 and DAC -0.3871 (attention
per 1,000). Table 3 with net aid: -0.1695, N 93, hc3 se 0.0551. unique-url
attention with net aid, log outcome: 0.224 (per 1,000, 3 decimals), N 100.

## table 1 recomputation (102 sample countries)

for each variable: N, mean, sd (ddof = 1; ddof = 0 also computed to see if
it matches the draft better), min, max, and the countries with the min and
the max. compared with the draft at the draft's precision (our value
rounded to the draft's decimals; a match means equal after rounding).

- attention share, unique urls, percent (x 100)
- matched usaid unique urls (`usaid_articles_unique`)
- total gdelt unique urls, thousands
- gross us oda, usd millions (`us_gross_mean`)
- gross dac oda, usd millions (`dac_gross_mean`)
- us share of gross dac oda, percent (x 100)
- gross us oda / gdp, percent: `us_gross_mean` x 1e6 / `gdp_avg` x 100
- gross dac oda / gdp, percent: `dac_gross_mean` x 1e6 / `gdp_avg` x 100
- days to first recorded coverage (raw days)

`gdp_avg` = wdi `NY.GDP.MKTP.CD` (current usd), 2018-2022 mean, as in
`gross_aid/followup`. countries with missing gdp are listed. sentence
checks of the draft: us share range and count below 1%; us aid range;
mean and sd of attention; timing range and mean delay among countries with
a date; number of countries without matched coverage.

## draft table 2 and results text

the draft numbers are expectations to compare against, not targets. code
is not changed to match them. every difference is reported. a draft value
is compared at its own precision; p written as "< 0.001" is a match if our
p < 0.001. where the draft does not state the outcome (restricted samples),
both attention outcomes are compared and reported.

## outputs (all in `gross_aid/share_main/`)

- `results.csv`: model, outcome, outcome_transform, sample, N, term,
  beta_hat, se_type, se, p, r2, note. one row per coefficient (intercept
  left out). attention beta and se times 1,000; days and negative
  binomial not scaled (said in note).
- `equivalence.csv`: the four checks per attention outcome with numbers and
  the max abs difference, plus the collinearity numbers.
- `table1_check.csv`: variable, N, mean, sd, min, max, draft values, match
  flags.
- `draft_check.csv`: item, draft value, our value, match flag.
- `log.txt`: all printed output, overwritten on each run.
- also logged: the largest abs difference between the raw share and
  ln(1 + share), and their pearson correlation.
