# more checks: small counts, how the two outcomes relate, population and gdp controls,
# and how many matched urls come from a domestic outlet (counts only)
# reads: data/input/, data/intermediate/ and world bank data from the api (network)
# writes: outputs/analysis_v5/ (tables and log). all regressions use hc3 se
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

import re
import sys
import urllib.parse
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm
import statsmodels.formula.api as smf
from lifelines import CoxPHFitter
from scipy import stats as sstats

np.random.seed(42)

OUT_DIR = config.OUT_ANALYSIS_V5
OUT_DIR.mkdir(exist_ok=True)
LOG_PATH = OUT_DIR / "log.txt"
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
print("outputs_v5: small-count sensitivity / outcome link / WDI controls / domestic-outlet feasibility")
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
print(f"N with total_articles merged: {df['total_articles'].notna().sum()}")

cc_raw = pd.read_csv(config.COUNTRY_CODES, dtype=str)
cc_raw["FIPS"] = cc_raw["FIPS"].astype(str).str.strip().str.upper()
fips_to_iso3 = dict(zip(cc_raw["FIPS"], cc_raw["ISO3166-1-Alpha-3"]))

m = pd.read_csv(config.MATCHES_ROWS, dtype=str, low_memory=False)
m["iso3"] = m["col_51"].astype(str).str.strip().str.upper().map(fips_to_iso3)
m = m.dropna(subset=["iso3"])
m["date_dt"] = pd.to_datetime(m["date"], format="%Y%m%d")
print(f"N matched rows total: {len(m)}  (after dropping rows with no FIPS->ISO3 match)")

usaid_unique = m.groupby("iso3")["col_57"].nunique().reset_index().rename(
    columns={"iso3": "ISO3", "col_57": "usaid_articles_unique"})
denom = pd.read_csv(config.TOTAL_UNIQUE_URL)

df = df.merge(usaid_unique, on="ISO3", how="left")
df = df.merge(denom, on="ISO3", how="left")
df["usaid_articles_unique"] = df["usaid_articles_unique"].fillna(0)
df["attention_share_unique"] = df["usaid_articles_unique"] / df["total_articles_unique_url"]
df["log_attention_share_unique"] = np.log1p(df["attention_share_unique"])
df["log_total_articles_unique"] = np.log(df["total_articles_unique_url"].where(df["total_articles_unique_url"] > 0))
print(f"N=102 base sample ready. N with usaid_articles_unique > 0: {(df['usaid_articles_unique']>0).sum()}")


def ols_pair_hc3(scenario, label, formula, data, coef="log_disbursements"):
    reg_vars = [coef] + [c.strip() for c in formula.split("~")[1].split("+")] + [formula.split("~")[0].strip()]
    reg_vars = list(dict.fromkeys(reg_vars))
    n_avail = data[reg_vars].dropna().shape[0]
    mr = smf.ols(formula, data=data).fit(cov_type="HC3")
    add(scenario, label, int(mr.nobs), mr.params[coef], "HC3", mr.bse[coef], mr.pvalues[coef])
    print(f"  {label}: N={int(mr.nobs)}  beta={mr.params[coef]:.6f}  HC3 SE={mr.bse[coef]:.6f}  p={mr.pvalues[coef]:.6f}")
    return mr


def run_cox(scenario, label, data, extra_cols=None):
    cols = ["days_to_first_article", "log_disbursements"] + (extra_cols or [])
    surv = data[cols].dropna(subset=[c for c in cols if c != "days_to_first_article"]).copy()
    surv["event"] = surv["days_to_first_article"].notna().astype(int)
    surv["time"] = surv["days_to_first_article"].fillna(365.0).clip(upper=365.0)
    cph = CoxPHFitter()
    fit_cols = ["time", "event", "log_disbursements"] + (extra_cols or [])
    cph.fit(surv[fit_cols], duration_col="time", event_col="event")
    coef = cph.params_["log_disbursements"]
    se = cph.standard_errors_["log_disbursements"]
    p = cph.summary.loc["log_disbursements", "p"]
    hr = np.exp(coef)
    n = len(surv)
    n_events = int(surv["event"].sum())
    add(scenario, f"{label} (HR={hr:.4f})", n, coef, "Cox model-based", se, p)
    print(f"  {label}: N={n}  events={n_events}  censored={n-n_events}  coef={coef:.6f}  SE={se:.6f}  p={p:.6g}  HR={hr:.4f}")
    return cph

# small-count sensitivity
print("\n" + "=" * 70)
print("PART A: SMALL-COUNT SENSITIVITY (restrict to usaid_articles_unique >= 5)")
print("=" * 70)

print(f"N before restriction: {len(df)}")
df_a = df[df["usaid_articles_unique"] >= 5].copy()
print(f"N after restricting to usaid_articles_unique >= 5: {len(df_a)}")
print(f"N with valid (positive) aid in restricted sample: {df_a['log_disbursements'].notna().sum()}")

ols_pair_hc3("small-count-5plus", "days ~ aid", "log_days ~ log_disbursements", df_a)
ols_pair_hc3("small-count-5plus", "days ~ aid + log_total_articles",
             "log_days ~ log_disbursements + log_total_articles", df_a)
ols_pair_hc3("small-count-5plus", "attention ~ aid (unique-URL)",
             "log_attention_share_unique ~ log_disbursements", df_a)

# negative binomial: usaid unique urls ~ aid, offset = log(total unique articles)
nb_data = df_a.dropna(subset=["usaid_articles_unique", "total_articles_unique_url", "log_disbursements"])
nb_data = nb_data[nb_data["total_articles_unique_url"] > 0]
print(f"\nNegative Binomial sample N: {len(nb_data)}")
nb_data = nb_data.copy()
nb_data["log_exposure"] = np.log(nb_data["total_articles_unique_url"])
negbin = smf.glm("usaid_articles_unique ~ log_disbursements", data=nb_data,
                  family=sm.families.NegativeBinomial(), offset=nb_data["log_exposure"]).fit()
add("small-count-5plus", "Negative Binomial: usaid unique URLs ~ aid, offset=log(total unique articles)",
    int(negbin.nobs), negbin.params["log_disbursements"], "model-based (MLE)",
    negbin.bse["log_disbursements"], negbin.pvalues["log_disbursements"])
print(f"  NegBin: N={int(negbin.nobs)}  beta={negbin.params['log_disbursements']:.6f}  "
      f"SE={negbin.bse['log_disbursements']:.6f}  p={negbin.pvalues['log_disbursements']:.6g}")

print()
run_cox("small-count-5plus", "Cox: days ~ aid, no volume", df_a)
run_cox("small-count-5plus", "Cox: days ~ aid + volume", df_a, extra_cols=["log_total_articles"])

# how the two outcomes relate (correlations)
print("\n" + "=" * 70)
print("PART B: OUTCOME LINK -- correlation of log(1+days) with attention share and URL count")
print("=" * 70)

sample_102 = df.copy()
sample_93 = df[df["log_days"].notna() & df["log_disbursements"].notna()].copy()
sample_100 = df[df["log_disbursements"].notna()].copy()
print(f"Sample 102 (full): N={len(sample_102)}")
print(f"Sample 93 (days-regression sample: article present and valid aid): N={len(sample_93)}")
print(f"Sample 100 (attention-regression sample: valid aid present): N={len(sample_100)}")

def report_corr(sample_name, data):
    print(f"\n--- {sample_name} ---")
    for other_label, other_col in [("unique-URL attention share", "attention_share_unique"),
                                     ("count of unique matched URLs", "usaid_articles_unique")]:
        pair = data[["log_days", other_col]].dropna()
        n_eff = len(pair)
        if n_eff < 3:
            print(f"  log(1+days) vs {other_label}: N too small ({n_eff}) to compute")
            continue
        pear = pair["log_days"].corr(pair[other_col], method="pearson")
        spear = pair["log_days"].corr(pair[other_col], method="spearman")
        print(f"  log(1+days) vs {other_label}: N={n_eff}  Pearson r={pear:.4f}  Spearman rho={spear:.4f}")

report_corr("Sample 102 (full)", sample_102)
report_corr("Sample 93 (days-regression sample)", sample_93)
report_corr("Sample 100 (attention-regression sample)", sample_100)

# wdi controls (population, gdp)
print("\n" + "=" * 70)
print("PART C: WDI CONTROLS (population SP.POP.TOTL, GDP NY.GDP.MKTP.CD, averaged 2018-2022)")
print("=" * 70)

def fetch_wdi(indicator):
    url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    params = {"date": "2018:2022", "format": "json", "per_page": 20000}
    r = requests.get(url, params=params, timeout=(10, 60))
    r.raise_for_status()
    payload = r.json()
    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError(f"Unexpected WDI response shape for {indicator}")
    records = payload[1]
    out = pd.DataFrame(records)
    return out

wdi_ok = True
try:
    pop_raw = fetch_wdi("SP.POP.TOTL")
    print(f"SP.POP.TOTL: fetched {len(pop_raw)} records")
    gdp_raw = fetch_wdi("NY.GDP.MKTP.CD")
    print(f"NY.GDP.MKTP.CD: fetched {len(gdp_raw)} records")
except Exception as e:
    wdi_ok = False
    msg = f"WDI download failed: {e}"
    print(msg)
    FAILURES.append(msg)

if wdi_ok:
    def avg_by_iso3(raw, value_name):
        raw = raw.copy()
        raw["countryiso3code"] = raw["countryiso3code"].astype(str).str.strip().str.upper()
        raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
        raw = raw[raw["countryiso3code"].str.len() == 3]
        avg = raw.groupby("countryiso3code")["value"].mean().reset_index()
        avg.columns = ["ISO3", value_name]
        return avg

    pop_avg = avg_by_iso3(pop_raw, "population_avg")
    gdp_avg = avg_by_iso3(gdp_raw, "gdp_avg")
    print(f"Population averaged: {pop_avg['population_avg'].notna().sum()} countries with a value")
    print(f"GDP averaged: {gdp_avg['gdp_avg'].notna().sum()} countries with a value")

    df = df.merge(pop_avg, on="ISO3", how="left").merge(gdp_avg, on="ISO3", how="left")
    df["log_population"] = np.log(df["population_avg"].where(df["population_avg"] > 0))
    df["log_gdp"] = np.log(df["gdp_avg"].where(df["gdp_avg"] > 0))

    missing_pop = df[df["population_avg"].isna()][["ISO3", "country"]]
    missing_gdp = df[df["gdp_avg"].isna()][["ISO3", "country"]]
    print(f"\nSample countries with missing population (2018-2022 avg), n={len(missing_pop)}:")
    print(missing_pop.to_string(index=False) if len(missing_pop) else "  none")
    print(f"\nSample countries with missing GDP (2018-2022 avg), n={len(missing_gdp)}:")
    print(missing_gdp.to_string(index=False) if len(missing_gdp) else "  none")

    pop_gdp_csv = df[["ISO3", "country", "population_avg", "gdp_avg"]]
    pop_gdp_csv.to_csv(OUT_DIR / "wdi_population_gdp.csv", index=False)
    print(f"\nWrote {OUT_DIR / 'wdi_population_gdp.csv'}")

    print("\n--- Re-running 4 main models + 2 Cox models, with log_population + log_gdp added ---")
    ols_pair_hc3("wdi-controls", "days ~ aid + pop + gdp",
                 "log_days ~ log_disbursements + log_population + log_gdp", df)
    ols_pair_hc3("wdi-controls", "days ~ aid + pop + gdp + volume",
                 "log_days ~ log_disbursements + log_population + log_gdp + log_total_articles", df)
    ols_pair_hc3("wdi-controls", "attention ~ aid + pop + gdp",
                 "log_attention_share_unique ~ log_disbursements + log_population + log_gdp", df)
    ols_pair_hc3("wdi-controls", "attention ~ aid + pop + gdp + volume",
                 "log_attention_share_unique ~ log_disbursements + log_population + log_gdp + log_total_articles_unique", df)
    print()
    run_cox("wdi-controls", "Cox: days ~ aid + pop + gdp, no volume", df, extra_cols=["log_population", "log_gdp"])
    run_cox("wdi-controls", "Cox: days ~ aid + pop + gdp + volume", df,
            extra_cols=["log_population", "log_gdp", "log_total_articles"])
else:
    print("Skipping all of Part C's model re-runs because the WDI download failed.")

# domestic outlets: counts only, no regressions
print("\n" + "=" * 70)
print("PART D: DOMESTIC-OUTLET FEASIBILITY (counts only)")
print("=" * 70)

def extract_domain(url):
    if not isinstance(url, str) or not url:
        return None
    u = url.strip()
    if not re.match(r"^https?://", u, re.IGNORECASE):
        u = "http://" + u
    try:
        netloc = urllib.parse.urlparse(u).netloc.lower()
    except Exception:
        return None
    netloc = netloc.split("@")[-1]  # strip userinfo
    netloc = netloc.split(":")[0]  # strip port
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc or None

m["domain"] = m["col_57"].apply(extract_domain)
n_with_domain = m["domain"].notna().sum()
print(f"N matched rows total: {len(m)}")
print(f"N matched rows with an extractable domain: {n_with_domain}")

unique_url_rows = m.dropna(subset=["col_57"]).drop_duplicates(subset=["iso3", "col_57"])
print(f"N unique (country, URL) pairs: {len(unique_url_rows)}")
unique_url_only = m.dropna(subset=["col_57"]).drop_duplicates(subset=["col_57"])
print(f"N unique URLs (ignoring country, since one URL could in principle appear under >1 country): {len(unique_url_only)}")

n_unique_domains = unique_url_only["domain"].nunique()
print(f"\nNumber of unique domains (across all unique URLs): {n_unique_domains}")

# cctld -> iso3 map from country-codes.csv (the 2-letter iso column, lowercased)
cc_raw2 = cc_raw.copy()
cc_raw2["ISO2"] = cc_raw2["ISO3166-1-Alpha-2"].astype(str).str.strip().str.lower()
cctld_to_iso3 = dict(zip(cc_raw2["ISO2"], cc_raw2["ISO3166-1-Alpha-3"]))
# known override: the uk uses .uk, not .gb
cctld_to_iso3["uk"] = "GBR"
KNOWN_CCTLDS = set(cctld_to_iso3.keys())
print(f"ccTLD list built from country-codes.csv: {len(KNOWN_CCTLDS)} codes (plus .uk override)")

def domain_cc(domain):
    if not domain:
        return None
    tld = domain.rsplit(".", 1)[-1]
    return tld if tld in KNOWN_CCTLDS else None

unique_url_only = unique_url_only.copy()
unique_url_only["domain_tld"] = unique_url_only["domain"].apply(lambda d: d.rsplit(".", 1)[-1] if d else None)
unique_url_only["has_cc_domain"] = unique_url_only["domain_tld"].isin(KNOWN_CCTLDS)

n_cc = unique_url_only["has_cc_domain"].sum()
n_total_urls = len(unique_url_only)
print(f"\nUnique URLs with a country-code-TLD domain: {n_cc} / {n_total_urls} = {n_cc/n_total_urls*100:.2f}%")
print("caveat: a ccTLD match is not proof of genuine domestic ownership -- several ccTLDs are used")
print("commercially worldwide regardless of country (.co, .io, .tv, .me, .ai, .fm among them). This")
print("is a string-level TLD check, not a verified ownership/registration check.")

non_cc = unique_url_only[~unique_url_only["has_cc_domain"]]
top50 = non_cc["domain"].value_counts().head(50)
top50.to_csv(OUT_DIR / "top50_domains_without_country_code.csv", header=["unique_url_count"])
print(f"\nTop 50 domains without a country-code TLD, by unique URL count (saved to "
      f"{OUT_DIR / 'top50_domains_without_country_code.csv'}):")
print(top50.to_string())

# per country: does the article's cctld match the event-location country?
m["domain_tld"] = m["domain"].apply(lambda d: d.rsplit(".", 1)[-1] if d else None)
m["domain_iso3"] = m["domain_tld"].map(cctld_to_iso3)
m["outlet_matches_event_country"] = m["domain_iso3"] == m["iso3"]

share_match_all_rows = m["outlet_matches_event_country"].mean()
n_match_rows = m["outlet_matches_event_country"].sum()
print(f"\nShare of all matched rows (n={len(m)}) where outlet-domain country == event-location country: "
      f"{n_match_rows} / {len(m)} = {share_match_all_rows*100:.2f}%")
print("(Rows where the domain had no recognizable ccTLD count as non-matching, by construction.)")

# per-country unique-url "domestic" counts
dedup_country_url = m.dropna(subset=["col_57"]).drop_duplicates(subset=["iso3", "col_57"])
domestic_unique = dedup_country_url[dedup_country_url["outlet_matches_event_country"]].groupby("iso3").size()
domestic_unique = domestic_unique.reindex(df["ISO3"].unique()).fillna(0)
n_ge3 = (domestic_unique >= 3).sum()
n_ge5 = (domestic_unique >= 5).sum()
print(f"\nCountries with >=3 matched unique URLs from outlets in the same country: {n_ge3}")
print(f"Countries with >=5 matched unique URLs from outlets in the same country: {n_ge5}")

domestic_unique_df = domestic_unique.reset_index()
domestic_unique_df.columns = ["ISO3", "domestic_unique_url_count"]
domestic_unique_df.to_csv(OUT_DIR / "domestic_outlet_counts_by_country.csv", index=False)
print(f"Wrote per-country domestic-outlet counts to {OUT_DIR / 'domestic_outlet_counts_by_country.csv'}")

# save the summary table and failures
summary = pd.DataFrame(summary_rows)
summary.to_csv(OUT_DIR / "summary_table.csv", index=False)
print(f"\n\nWrote {len(summary)} rows to {OUT_DIR / 'summary_table.csv'}")
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
print("outputs_v5 RUN COMPLETE")
print("=" * 70)
