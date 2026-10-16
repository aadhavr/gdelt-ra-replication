# spec: gross us aid as a new aid measure (written before any model was run)

## aid measures

- net (existing): `us_oda_disbursements` in `data/input/3-29-v2_oda_data.csv`,
  kept as `us_net`. table label: "US aid (USD millions) (net)".
- gross (new): oecd dac2a, measure 240 (gross oda), disbursements, constant
  2024 prices, usd millions. `us_gross_mean` = sum of the 2018-2022 values / 5,
  a missing year counts as 0. table label: "US aid (USD millions) (gross)".
- `dac_gross_mean`: the same for the dac countries total.
- `us_share` = `us_gross_mean` / `dac_gross_mean`.
- the regressor is the natural log of the aid variable. a value <= 0 gives a
  missing log, so the country leaves that model (same rule as build_all.py).

## primary specification

the primary specification is the same as tables 3 and 4, with gross us aid in
place of net:

- table 3: log(1 + days to first article) ~ log aid, ols, hc3.
- table 4: log(1 + unique-url attention share) ~ log aid, ols, hc3. beta-hat
  and se are shown per 1,000, as in table 4.

## models

all models below are reported. none are added or dropped. net and gross
results are shown side by side. no direction is chosen after seeing results.

each of g1 to g7 runs twice: net aid, then gross us aid. each runs on the
countries with a valid log of its own aid variable.

- g1: days ~ log aid
- g2: attention ~ log aid
- g3: days ~ log aid + log(total unique articles)
- g4: attention ~ log aid + log(total unique articles)
- g5: cox, days to first article ~ log aid, with and without log(total unique
  articles). the 7 no-article countries are censored at 365 days (as in b2).
- g6: negative binomial glm (alpha 1, as in b3), unique matched urls ~ log aid,
  offset log(total unique articles)
- g7: days ~ log aid + log population + log gdp, and attention ~ the same
  (wdi snapshot, `data/input/wdi_population_gdp.csv`)
- g8 (gross only): outcome ~ log us_gross + log dac_gross, for days and for
  attention. both coefficients, pearson correlation of the two logs,
  vif = 1 / (1 - r^2), and an hc3 wald test that both coefficients are 0.
- g9 (gross only): outcome ~ log us_share, for days and for attention.

negative-aid check:

- list the countries in the gross sample that are not in the net sample
  (expected egy and gab). print their aid, days and share.
- g1 to g4 with gross aid on the same countries as the net sample.

count: g1 to g7 = 9 models x 2 aid measures = 18; g1 to g4 gross on the net
sample = 4; g8 = 2; g9 = 2. total 26 models.

## standard errors

- ols: hc3, as in build_all.py.
- cox (g5) and negative binomial (g6): model-based se, as in b2 and b3 of
  build_all.py. hc3 is not defined for the cox model.
- r2 is reported for ols only.

## reporting

- beta-hat, se, p, r2 and n for each model.
- no statement that a result supports or rejects salience or dampening.
