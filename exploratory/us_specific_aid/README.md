# US-specific versus general aid dependency: replication extension

Exploratory, not in the paper. This was received as a standalone extension
(folder `usaid_aid_dependency_replication/`: `run_analysis.py`, `README.md`,
`results/us_specific_results.csv`) and added here with only these changes:
paths come from `config.py` instead of `--repo` / `--output`, outputs go to
this folder, and printed output is also written to `log.txt`. The variables,
sample and models are unchanged. Unlike the other exploratory folders, there is
no `PREDICTIONS.md`, because the extension came with no predictions written
before the models were run.

Reproduction check: `us_specific_results.csv` here is byte-identical to the
output of the unmodified `run_analysis.py` on this repo. It differs from the
`results/us_specific_results.csv` that came with the extension only by
floating-point noise (max relative difference 4.4e-13). That file was made in
a different environment. The extension's README lists `analysis_sample.csv` as
an output, but that file was not in the folder that was received.

## Run

From the repository root:

```bash
python exploratory/us_specific_aid/run_us_specific_aid.py
```

Inputs:

- `data/input/3-29-v2_oda_data.csv` (US aid, millions of dollars)
- `data/input/3_29__oda_data.csv` (total ODA, millions; first three rows skipped)
- `data/input/wdi_population_gdp.csv` (GDP in dollars)
- `data/intermediate/country_reaction_dataset.csv` (matched GDELT event rows and total GDELT event rows)

Outputs: `us_specific_results.csv` (coefficients and inference), `analysis_sample.csv` (the 98-country complete-case analysis sample), `log.txt`.

## Variables and specification (from the extension's README)

- `us_gdp = us_aid_m * 1,000,000 / gdp_avg`
- `oda_gdp = total_oda_m * 1,000,000 / gdp_avg`
- `us_oda_share = us_aid_m / total_oda_m`
- Explanatory variables enter as natural logarithms; nonpositive values are excluded.
- Outcome: `usaid_articles`, the count of **matched GDELT event rows** from the student's analytical dataset (not verified unique news articles).
- All regressions: negative-binomial **GLM with dispersion alpha fixed at 1**, log(total GDELT event rows) as an exposure offset, HC3 robust standard errors. The fixed dispersion is a modeling choice, not an estimated dispersion parameter.
- All full-sample models use the same complete-case country sample. The restriction uses **at least five matched event rows**, *not* at least five unique URLs, so it is not directly equivalent to Aadhav's five-URL sensitivity analysis.
- The models compare conditional associations; they do not identify causal effects. `US aid/GDP = (total ODA/GDP) * (US aid/total ODA)`, so the regressors are mathematically linked and multicollinearity is possible.

## Important verification before publication (from the extension's README)

Check the provenance, units and net/gross definitions of the ODA fields, whether the outcome counts event rows versus unique URLs, the consequences of fixing alpha at 1, and sensitivity to the five-*unique*-URL sample. This code reproduces an exploratory analysis, not a validated final paper specification.

## Follow-up checks (`run_us_specific_aid_checks.py`)

Added in this repo (not part of the extension). Run from the repository root:

```bash
python exploratory/us_specific_aid/run_us_specific_aid_checks.py
```

It rebuilds the data the same way as `run_us_specific_aid.py` and adds:

1. **Unique-URL counts.** Outcome = unique matched URLs per country, offset = log
   total unique URLs (`total_articles_unique_url`). This is the same
   construction as `robustness/build_all.py`. The restricted sample is
   **>= 5 unique URLs**, the same cutoff as `robustness/analysis.py` part A.
2. **Collinearity.** Pearson and Spearman correlations between log US aid/GDP
   and log total ODA/GDP, the VIF (1 / (1 - r^2)), and an HC3 Wald test that
   both coefficients are 0 in the joint model. `log_us_gdp = log_oda_gdp +
   log_us_oda_share` exactly, so the models "US aid/GDP + total ODA/GDP" and
   "total ODA/GDP + US share of ODA" are the same model with different
   parameters.
3. **Negative net aid.** The aid source is net ODA disbursements (DAC2A
   measure 206), which can be negative. The log of a nonpositive ratio is
   missing, so Egypt (US net aid -23.7) and Gabon (-1.2) leave the sample
   without any message. South Sudan and Eritrea leave it because the WDI
   snapshot has no GDP for them. A sensitivity sets nonpositive US aid to the
   smallest positive value in the sample (0.7). This choice is arbitrary.

Every model is run for both count types and both treatments of aid
(as published, bottom-coded). The event-row, as-published rows reproduce
`us_specific_results.csv`.

Outputs: `checks_results.csv`, `checks_collinearity.csv`, `checks_negative_aid.csv`, `checks_log.txt`.

