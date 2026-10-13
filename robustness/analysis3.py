# more checks: profile of the 7 no-article countries, the imputed y-values and full
# tests for the 365/145 imputation, and ols and cox on n=91 vs n=98 (7 imputed at 365)
# reads: data/input/, data/intermediate/ and world bank data from the api (network)
# writes: outputs/analysis_v5/ (tables and log)
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm
import statsmodels.formula.api as smf
from lifelines import CoxPHFitter

np.random.seed(42)

OUT_DIR = config.OUT_ANALYSIS_V5
LOG_PATH = OUT_DIR / "log3.txt"
FAILURES = []


class Tee:
    def __init__(self, path, mode="w"):
        self.file = open(path, mode)
        self.stdout = sys.stdout

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


sys.stdout = Tee(LOG_PATH, "w")
print("=" * 70)
print("outputs_v5 FOLLOW-UP 2: E no-article country profile, F C2 re-check, G 91-vs-98imputed comparison")
print("=" * 70)

summary_rows = []
def add(scenario, model, n, est, se_type, se, p):
    summary_rows.append({"scenario": scenario, "model": model, "N": n, "estimate": est, "SE type": se_type, "SE": se, "p": p})

# base data
print("\n" + "-" * 70)
print("LOADING BASE DATA")
print("-" * 70)

df = pd.read_csv(config.ODA_DATA)
df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()
df["us_oda_disbursements"] = df["us_oda_disbursements"].astype(str).str.replace(",", "")
df["us_oda_disbursements"] = pd.to_numeric(df["us_oda_disbursements"], errors="coerce")
df["days_to_first_article"] = pd.to_numeric(df["days_to_first_article"], errors="coerce")
df["log_days"] = np.log1p(df["days_to_first_article"])
df["log_disbursements"] = np.where(df["us_oda_disbursements"] > 0, np.log(df["us_oda_disbursements"]), np.nan)
print(f"N rows loaded: {len(df)}")

crd = pd.read_csv(config.COUNTRY_REACTION).rename(columns={"iso3": "ISO3"})[["ISO3", "total_articles"]]
crd["ISO3"] = crd["ISO3"].astype(str).str.strip().str.upper()
df = df.merge(crd, on="ISO3", how="left")
df["log_total_articles"] = np.log(df["total_articles"].where(df["total_articles"] > 0))

denom = pd.read_csv(config.TOTAL_UNIQUE_URL)
df = df.merge(denom, on="ISO3", how="left")
print(f"N with total_articles_unique_url merged: {df['total_articles_unique_url'].notna().sum()}")

def fetch_wdi(indicator):
    url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    params = {"date": "2018:2022", "format": "json", "per_page": 20000}
    r = requests.get(url, params=params, timeout=(10, 60))
    r.raise_for_status()
    return pd.DataFrame(r.json()[1])

def avg_by_iso3(raw, value_name):
    raw = raw.copy()
    raw["countryiso3code"] = raw["countryiso3code"].astype(str).str.strip().str.upper()
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    raw = raw[raw["countryiso3code"].str.len() == 3]
    avg = raw.groupby("countryiso3code")["value"].mean().reset_index()
    avg.columns = ["ISO3", value_name]
    return avg

wdi_ok = True
try:
    pop_avg = avg_by_iso3(fetch_wdi("SP.POP.TOTL"), "population_avg")
    gdp_avg = avg_by_iso3(fetch_wdi("NY.GDP.MKTP.CD"), "gdp_avg")
    df = df.merge(pop_avg, on="ISO3", how="left").merge(gdp_avg, on="ISO3", how="left")
    df["log_population"] = np.log(df["population_avg"].where(df["population_avg"] > 0))
    df["log_gdp"] = np.log(df["gdp_avg"].where(df["gdp_avg"] > 0))
    print(f"WDI re-fetched OK. Population missing: {df['population_avg'].isna().sum()}, "
          f"GDP missing: {df['gdp_avg'].isna().sum()}")
except Exception as e:
    wdi_ok = False
    msg = f"WDI re-fetch failed: {e}"
    print(msg)
    FAILURES.append(msg)

NO_ARTICLE_7 = ["TUN", "GEO", "BDI", "BOL", "MRT", "DZA", "GNB"]

# no-article country profile
print("\n" + "=" * 70)
print("PART E: profile of the 7 no-article countries")
print("=" * 70)

df["rank_total_articles_unique"] = df["total_articles_unique_url"].rank(method="min", ascending=True)
print(f"N countries ranked: {df['total_articles_unique_url'].notna().sum()} (1 = fewest unique GDELT articles)")

e_table = df[df["ISO3"].isin(NO_ARTICLE_7)][
    ["ISO3", "country", "us_oda_disbursements", "total_articles_unique_url",
     "population_avg", "gdp_avg", "rank_total_articles_unique"]
].sort_values("rank_total_articles_unique")
e_table = e_table.rename(columns={
    "us_oda_disbursements": "aid_usd_millions",
    "total_articles_unique_url": "total_unique_gdelt_articles",
    "population_avg": "population_avg_2018_2022",
    "gdp_avg": "gdp_avg_2018_2022_usd",
    "rank_total_articles_unique": "rank_of_total_articles_among_102",
})
print("\n" + e_table.to_string(index=False))
e_table.to_csv(OUT_DIR / "no_article_country_profile.csv", index=False)
print(f"\nWrote {OUT_DIR / 'no_article_country_profile.csv'}")
print(f"\n(For reference: N=102 total countries ranked; rank 1 = lowest total_unique_gdelt_articles.)")

# imputation re-check: the imputed y-values and full test statistics
print("\n" + "=" * 70)
print("PART F: C2 re-check -- imputed y-values, coefficient, HC3 SE, t-statistic, p-value (6 dp)")
print("=" * 70)

if wdi_ok:
    for impute_val in [365.0, 145.0]:
        print(f"\n--- impute = {impute_val} days ---")
        df_imp = df.copy()
        df_imp.loc[df_imp["ISO3"].isin(NO_ARTICLE_7), "days_to_first_article"] = impute_val
        df_imp["log_days"] = np.log1p(df_imp["days_to_first_article"])

        imputed_rows = df_imp[df_imp["ISO3"].isin(NO_ARTICLE_7)][["ISO3", "country", "days_to_first_article", "log_days"]]
        print("Imputed y-values (days_to_first_article and log(1+days)) for the 7 countries:")
        print(imputed_rows.to_string(index=False))

        formula = "log_days ~ log_disbursements + log_population + log_gdp"
        reg_data = df_imp[["log_days", "log_disbursements", "log_population", "log_gdp"]].dropna()
        n = len(reg_data)
        mr = smf.ols(formula, data=df_imp).fit(cov_type="HC3")
        coef = mr.params["log_disbursements"]
        se = mr.bse["log_disbursements"]
        t_stat = mr.tvalues["log_disbursements"]
        p_val = mr.pvalues["log_disbursements"]
        print(f"\nN={n}")
        print(f"Coefficient (log_disbursements): {coef:.6f}")
        print(f"HC3 Standard Error:               {se:.6f}")
        print(f"t-statistic:                       {t_stat:.6f}")
        print(f"p-value:                           {p_val:.6f}")
        add(f"recheck-impute-{int(impute_val)}", f"days ~ aid + pop + gdp (impute={int(impute_val)})",
            n, coef, "HC3", se, p_val)

    # check that the outcome differs between the two runs
    df_365 = df.copy()
    df_365.loc[df_365["ISO3"].isin(NO_ARTICLE_7), "days_to_first_article"] = 365.0
    df_365["log_days"] = np.log1p(df_365["days_to_first_article"])

    df_145 = df.copy()
    df_145.loc[df_145["ISO3"].isin(NO_ARTICLE_7), "days_to_first_article"] = 145.0
    df_145["log_days"] = np.log1p(df_145["days_to_first_article"])

    compare = pd.DataFrame({
        "ISO3": NO_ARTICLE_7,
        "log_days_impute_365": df_365.set_index("ISO3").loc[NO_ARTICLE_7, "log_days"].values,
        "log_days_impute_145": df_145.set_index("ISO3").loc[NO_ARTICLE_7, "log_days"].values,
    })
    compare["identical"] = compare["log_days_impute_365"] == compare["log_days_impute_145"]
    print("\n--- Confirmation that the dependent variable actually differs between the two runs ---")
    print(compare.to_string(index=False))
    all_identical = compare["identical"].all()
    print(f"\nAll 7 values identical between runs: {all_identical}  "
          f"(expected: False -- log(1+365)={np.log1p(365):.6f} vs log(1+145)={np.log1p(145):.6f})")
    if all_identical:
        FAILURES.append("BUG CONFIRMED: log_days values for the 7 imputed countries did not differ between the 365 and 145 runs.")
else:
    print("Skipped: WDI fetch failed (see failures).")

# days ~ aid + pop + gdp (with and without volume) and cox, n=91 vs n=98 (impute 365)
print("\n" + "=" * 70)
print("PART G: 91 (censored dropped) vs 98 (7 set to log(1+365), treated as real events) -- OLS and Cox")
print("=" * 70)

if wdi_ok:
    df_91 = df[df["days_to_first_article"].notna()].copy()
    print(f"\nN=91 sample (countries with an observed first-article date): {len(df_91)}")

    df_98 = df.copy()
    df_98.loc[df_98["ISO3"].isin(NO_ARTICLE_7), "days_to_first_article"] = 365.0
    df_98["log_days"] = np.log1p(df_98["days_to_first_article"])
    print(f"N=98 sample (7 no-article countries set to day 365, treated as real observed values): {len(df_98[df_98['log_disbursements'].notna()])}")

    def ols_hc3(scenario, label, formula, data, coef="log_disbursements"):
        mr = smf.ols(formula, data=data).fit(cov_type="HC3")
        add(scenario, label, int(mr.nobs), mr.params[coef], "HC3", mr.bse[coef], mr.pvalues[coef])
        print(f"  {label}: N={int(mr.nobs)}  beta={mr.params[coef]:.6f}  HC3 SE={mr.bse[coef]:.6f}  p={mr.pvalues[coef]:.6f}")

    print("\n--- N=91 (censored dropped) ---")
    ols_hc3("n91-dropped", "days ~ aid + pop + gdp",
            "log_days ~ log_disbursements + log_population + log_gdp", df_91)
    ols_hc3("n91-dropped", "days ~ aid + pop + gdp + volume",
            "log_days ~ log_disbursements + log_population + log_gdp + log_total_articles", df_91)

    print("\n--- N=98 (7 set to day 365, as real values) ---")
    ols_hc3("n98-impute365", "days ~ aid + pop + gdp",
            "log_days ~ log_disbursements + log_population + log_gdp", df_98)
    ols_hc3("n98-impute365", "days ~ aid + pop + gdp + volume",
            "log_days ~ log_disbursements + log_population + log_gdp + log_total_articles", df_98)

    # cox on the same two samples. with n=91 every case has an article, so none is censored.
    # with n=98 the 7 get event=1 at t=365 (not the usual censoring), so ols and cox treat
    # them the same way. this tests if the ols/cox gap came from imputation vs censoring
    def run_cox_explicit(scenario, label, data, event_override_iso3=None, event_override_time=None, extra_cols=None):
        cols = ["ISO3", "days_to_first_article", "log_disbursements"] + (extra_cols or [])
        d = data[cols].dropna(subset=[c for c in cols if c not in ("days_to_first_article", "ISO3")]).copy()
        d["event"] = d["days_to_first_article"].notna().astype(int)
        d["time"] = d["days_to_first_article"].fillna(365.0).clip(upper=365.0)
        if event_override_iso3:
            mask = d["ISO3"].isin(event_override_iso3)
            d.loc[mask, "event"] = 1
            d.loc[mask, "time"] = event_override_time
        cph = CoxPHFitter()
        fit_cols = ["time", "event", "log_disbursements"] + (extra_cols or [])
        cph.fit(d[fit_cols], duration_col="time", event_col="event")
        coef = cph.params_["log_disbursements"]
        se = cph.standard_errors_["log_disbursements"]
        p = cph.summary.loc["log_disbursements", "p"]
        hr = np.exp(coef)
        n = len(d)
        n_events = int(d["event"].sum())
        add(scenario, f"{label} (HR={hr:.4f})", n, coef, "Cox model-based", se, p)
        print(f"  {label}: N={n}  events={n_events}  censored={n-n_events}  coef={coef:.6f}  SE={se:.6f}  p={p:.6g}  HR={hr:.4f}")

    print("\n--- Cox, N=91 (censored dropped; zero censoring possible) ---")
    run_cox_explicit("n91-dropped", "Cox: days ~ aid + pop + gdp + volume",
                      df_91, extra_cols=["log_population", "log_gdp", "log_total_articles"])

    print("\n--- Cox, N=98 (7 set to an explicit event at t=365, not censored) ---")
    run_cox_explicit("n98-impute365", "Cox: days ~ aid + pop + gdp + volume",
                      df, event_override_iso3=NO_ARTICLE_7, event_override_time=365.0,
                      extra_cols=["log_population", "log_gdp", "log_total_articles"])
else:
    print("Skipped: WDI fetch failed (see failures).")

# save the summary and failures
summary = pd.DataFrame(summary_rows)
summary.to_csv(OUT_DIR / "summary_table3.csv", index=False)
print(f"\n\nWrote {len(summary)} rows to {OUT_DIR / 'summary_table3.csv'}")
print(summary.to_string(index=False))

print("\n" + "-" * 70)
print("FAILURES")
print("-" * 70)
if FAILURES:
    for f in FAILURES:
        print(f"  - {f}")
else:
    print("  none")

print("\n" + "=" * 70)
print("outputs_v5 FOLLOW-UP 2 COMPLETE")
print("=" * 70)
