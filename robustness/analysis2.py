# more checks: a median split that does not use the outcome, cox censoring comparison,
# days ~ aid + pop + gdp with the 7 no-article countries imputed, hand-coded news domains
# reads: data/input/, data/intermediate/ and world bank data from the api (network)
# writes: outputs/analysis_v5/ (tables and log)
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

np.random.seed(42)

OUT_DIR = config.OUT_ANALYSIS_V5
LOG_PATH = OUT_DIR / "log2.txt"
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
print("outputs_v5 FOLLOW-UP: A2 median-split, B2 Cox censoring, C2 365/145 impute, D2 hand-coded domains")
print("=" * 70)

summary_rows = []
def add(scenario, model, n, est, se_type, se, p):
    summary_rows.append({"scenario": scenario, "model": model, "N": n, "estimate": est, "SE type": se_type, "SE": se, "p": p})

# base data (same as analysis.py, with the wdi download)
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

cc_raw = pd.read_csv(config.COUNTRY_CODES, dtype=str)
cc_raw["FIPS"] = cc_raw["FIPS"].astype(str).str.strip().str.upper()
fips_to_iso3 = dict(zip(cc_raw["FIPS"], cc_raw["ISO3166-1-Alpha-3"]))

m = pd.read_csv(config.MATCHES_ROWS, dtype=str, low_memory=False)
m["iso3"] = m["col_51"].astype(str).str.strip().str.upper().map(fips_to_iso3)
m = m.dropna(subset=["iso3"])
m["date_dt"] = pd.to_datetime(m["date"], format="%Y%m%d")
print(f"N matched rows (valid ISO3): {len(m)}")

usaid_unique = m.groupby("iso3")["col_57"].nunique().reset_index().rename(
    columns={"iso3": "ISO3", "col_57": "usaid_articles_unique"})
denom = pd.read_csv(config.TOTAL_UNIQUE_URL)

df = df.merge(usaid_unique, on="ISO3", how="left")
df = df.merge(denom, on="ISO3", how="left")
df["usaid_articles_unique"] = df["usaid_articles_unique"].fillna(0)
df["attention_share_unique"] = df["usaid_articles_unique"] / df["total_articles_unique_url"]
df["log_attention_share_unique"] = np.log1p(df["attention_share_unique"])
df["log_total_articles_unique"] = np.log(df["total_articles_unique_url"].where(df["total_articles_unique_url"] > 0))

# wdi is downloaded again here, so this script does not need another script's output
def fetch_wdi(indicator):
    url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    params = {"date": "2018:2022", "format": "json", "per_page": 20000}
    r = requests.get(url, params=params, timeout=(10, 60))
    r.raise_for_status()
    payload = r.json()
    return pd.DataFrame(payload[1])

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
    pop_raw = fetch_wdi("SP.POP.TOTL")
    gdp_raw = fetch_wdi("NY.GDP.MKTP.CD")
    pop_avg = avg_by_iso3(pop_raw, "population_avg")
    gdp_avg = avg_by_iso3(gdp_raw, "gdp_avg")
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

print(f"\nN=102 base sample ready. N with valid aid (log_disbursements): {df['log_disbursements'].notna().sum()}")


def ols_hc3(scenario, label, formula, data, coef="log_disbursements"):
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

# median split that does not use the outcome
print("\n" + "=" * 70)
print("PART A2: median split on total_articles_unique_url (not an outcome variable) within the N=100 valid-aid sample")
print("=" * 70)

sample100 = df[df["log_disbursements"].notna()].copy()
print(f"N valid-aid sample: {len(sample100)}")
med = sample100["total_articles_unique_url"].median()
print(f"Median of total_articles_unique_url: {med}")

low_half = sample100[sample100["total_articles_unique_url"] <= med].copy()
high_half = sample100[sample100["total_articles_unique_url"] > med].copy()
print(f"Low half (<= median): N={len(low_half)}")
print(f"High half (> median): N={len(high_half)}")

for half_name, half_df in [("low-volume-half", low_half), ("high-volume-half", high_half)]:
    print(f"\n--- {half_name} (N={len(half_df)}) ---")
    ols_hc3(half_name, "days ~ aid", "log_days ~ log_disbursements", half_df)
    ols_hc3(half_name, "days ~ aid + log_total_articles", "log_days ~ log_disbursements + log_total_articles", half_df)
    ols_hc3(half_name, "attention ~ aid (unique-URL)", "log_attention_share_unique ~ log_disbursements", half_df)

    nb_data = half_df.dropna(subset=["usaid_articles_unique", "total_articles_unique_url", "log_disbursements"])
    nb_data = nb_data[nb_data["total_articles_unique_url"] > 0].copy()
    print(f"  NegBin sample N: {len(nb_data)}")
    if len(nb_data) >= 5:
        nb_data["log_exposure"] = np.log(nb_data["total_articles_unique_url"])
        try:
            negbin = smf.glm("usaid_articles_unique ~ log_disbursements", data=nb_data,
                              family=sm.families.NegativeBinomial(), offset=nb_data["log_exposure"]).fit()
            add(half_name, "Negative Binomial: usaid unique URLs ~ aid, offset=log(total unique articles)",
                int(negbin.nobs), negbin.params["log_disbursements"], "model-based (MLE)",
                negbin.bse["log_disbursements"], negbin.pvalues["log_disbursements"])
            print(f"  NegBin: N={int(negbin.nobs)}  beta={negbin.params['log_disbursements']:.6f}  "
                  f"SE={negbin.bse['log_disbursements']:.6f}  p={negbin.pvalues['log_disbursements']:.6g}")
        except Exception as e:
            print(f"  NegBin failed: {e}")
            FAILURES.append(f"{half_name} NegBin failed: {e}")
    else:
        print("  NegBin skipped: sample too small")

    run_cox(half_name, "Cox: days ~ aid, no volume", half_df)
    run_cox(half_name, "Cox: days ~ aid + volume", half_df, extra_cols=["log_total_articles"])

# cox censoring comparison (n=98 vs n=91, pop + gdp + volume)
print("\n" + "=" * 70)
print("PART B2: Cox with pop+gdp+volume -- N=98 (with censoring) vs N=91 (censored dropped)")
print("=" * 70)

if wdi_ok:
    print("\n--- N=98 (7 censored countries kept, event=0 at t=365) ---")
    run_cox("cox-censoring-full", "Cox: days ~ aid + pop + gdp + volume (N=98, censored kept)",
            df, extra_cols=["log_population", "log_gdp", "log_total_articles"])

    print("\n--- N=91 (7 no-article countries dropped entirely) ---")
    df_91 = df[df["days_to_first_article"].notna()].copy()
    print(f"N with an observed first-article date: {len(df_91)}")
    run_cox("cox-censoring-dropped", "Cox: days ~ aid + pop + gdp + volume (N=91, censored dropped)",
            df_91, extra_cols=["log_population", "log_gdp", "log_total_articles"])
    print("\nNote: with censored observations dropped, every remaining case is an event, so this Cox")
    print("run and a plain OLS on log(1+days) over the same 91 cases are testing very similar things;")
    print("a large gap between the N=98 and N=91 Cox results would show the censored cases are doing")
    print("real work, not just adding noise.")
else:
    print("Skipped: WDI fetch failed (see failures).")

# ols days ~ aid + pop + gdp, 7 no-article countries imputed at 365 and 145
print("\n" + "=" * 70)
print("PART C2: OLS days ~ aid + pop + gdp, no-article countries imputed at day 365, then day 145")
print("=" * 70)

if wdi_ok:
    NO_ARTICLE_7 = ["TUN", "GEO", "BDI", "BOL", "MRT", "DZA", "GNB"]
    for impute_val in [365.0, 145.0]:
        df_imp = df.copy()
        n_before = df_imp["days_to_first_article"].notna().sum()
        df_imp.loc[df_imp["ISO3"].isin(NO_ARTICLE_7), "days_to_first_article"] = impute_val
        n_after = df_imp["days_to_first_article"].notna().sum()
        df_imp["log_days"] = np.log1p(df_imp["days_to_first_article"])
        print(f"\n--- impute = {impute_val} days ---")
        print(f"N with a days value before imputation: {n_before}  after: {n_after}")
        ols_hc3(f"impute-{int(impute_val)}-pop-gdp", f"days ~ aid + pop + gdp (impute={int(impute_val)})",
                "log_days ~ log_disbursements + log_population + log_gdp", df_imp)
else:
    print("Skipped: WDI fetch failed (see failures).")

# hand-coded domain country check
print("\n" + "=" * 70)
print("PART D2: hand-coded outlet country for top-50 non-ccTLD domains (only where confidently known)")
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
    netloc = netloc.split("@")[-1].split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc or None

m["domain"] = m["col_57"].apply(extract_domain)
unique_url_only = m.dropna(subset=["col_57"]).drop_duplicates(subset=["col_57"]).copy()
unique_url_only["domain_tld"] = unique_url_only["domain"].apply(lambda d: d.rsplit(".", 1)[-1] if d else None)

cc_raw2 = cc_raw.copy()
cc_raw2["ISO2"] = cc_raw2["ISO3166-1-Alpha-2"].astype(str).str.strip().str.lower()
cctld_to_iso3 = dict(zip(cc_raw2["ISO2"], cc_raw2["ISO3166-1-Alpha-3"]))
cctld_to_iso3["uk"] = "GBR"
KNOWN_CCTLDS = set(cctld_to_iso3.keys())
unique_url_only["has_cc_domain"] = unique_url_only["domain_tld"].isin(KNOWN_CCTLDS)
non_cc = unique_url_only[~unique_url_only["has_cc_domain"]]
top50 = non_cc["domain"].value_counts().head(50)

# hand-coded, conservative: only domains whose home country is well known.
# left out: outlets with editions in several countries (theconversation.com) and
# outlets with an unclear home country: bignewsnetwork.com, africanews.com, econotimes.com
HAND_CODED = {
    "yahoo.com": "USA", "theguardian.com": "GBR", "nbcconnecticut.com": "USA",
    "timesofindia.indiatimes.com": "IND", "hindustantimes.com": "IND", "newsweek.com": "USA",
    "marketscreener.com": "FRA", "frontpageafricaonline.com": "LBR", "winnipegfreepress.com": "CAN",
    "forbes.com": "USA", "nbcnews.com": "USA", "foxnews.com": "USA", "bostonglobe.com": "USA",
    "indianexpress.com": "IND", "economictimes.indiatimes.com": "IND", "thedailystar.net": "BGD",
    "nypost.com": "USA", "cbsnews.com": "USA", "christianitytoday.com": "USA", "columbian.com": "USA",
    "breitbart.com": "USA", "aol.com": "USA", "dw.com": "DEU", "abcnews.go.com": "USA",
    "firstpost.com": "IND", "businessinsider.com": "USA", "ncronline.org": "USA", "newsday.com": "USA",
    "nbcphiladelphia.com": "USA", "nbcsandiego.com": "USA", "thehill.com": "USA",
    "naturalnews.com": "USA", "76crimes.com": "USA", "myjoyonline.com": "GHA", "adn.com": "USA",
    "thefrontierpost.com": "PAK", "ibtimes.com": "USA", "eco-business.com": "SGP",
    "theepochtimes.com": "USA", "naija247news.com": "NGA", "kathmandupost.com": "NPL",
    "nbcnewyork.com": "USA", "moneycontrol.com": "IND", "foreignpolicy.com": "USA",
    "nbclosangeles.com": "USA", "thehindu.com": "IND",
}
LEFT_UNKNOWN = ["bignewsnetwork.com", "africanews.com", "theconversation.com", "econotimes.com"]

print(f"Top 50 non-ccTLD domains: {len(top50)}")
print(f"Hand-coded with a confident country: {len(HAND_CODED)}")
print(f"Left unknown (ambiguous HQ, multi-edition, or not confidently verifiable): {len(LEFT_UNKNOWN)}")
print("\nTop 50, with hand-coded country where known:")
for dom, cnt in top50.items():
    country = HAND_CODED.get(dom, "UNKNOWN" if dom in LEFT_UNKNOWN else "UNKNOWN (not coded)")
    print(f"  {dom:<32} unique_urls={cnt:<5} country={country}")

hand_coded_table = pd.DataFrame(
    [{"domain": dom, "unique_url_count": cnt, "hand_coded_country": HAND_CODED.get(dom, "UNKNOWN")}
     for dom, cnt in top50.items()]
)
hand_coded_table.to_csv(OUT_DIR / "top50_domains_hand_coded.csv", index=False)
print(f"\nWrote {OUT_DIR / 'top50_domains_hand_coded.csv'}")

# count the cctld-based domestic matches again, then add the hand-coded ones
m["domain_tld"] = m["domain"].apply(lambda d: d.rsplit(".", 1)[-1] if d else None)
m["domain_iso3_cctld"] = m["domain_tld"].map(cctld_to_iso3)
m["domain_iso3_handcoded"] = m["domain"].map(HAND_CODED)
# combined: use the cctld match first, then the hand-coded one for other domains
m["domain_iso3_combined"] = m["domain_iso3_cctld"].fillna(m["domain_iso3_handcoded"])
m["outlet_matches_event_country_cctld_only"] = m["domain_iso3_cctld"] == m["iso3"]
m["outlet_matches_event_country_combined"] = m["domain_iso3_combined"] == m["iso3"]

dedup_country_url = m.dropna(subset=["col_57"]).drop_duplicates(subset=["iso3", "col_57"])
before = dedup_country_url[dedup_country_url["outlet_matches_event_country_cctld_only"]].groupby("iso3").size()
after = dedup_country_url[dedup_country_url["outlet_matches_event_country_combined"]].groupby("iso3").size()

before = before.reindex(df["ISO3"].unique()).fillna(0)
after = after.reindex(df["ISO3"].unique()).fillna(0)

n_ge5_before = (before >= 5).sum()
n_ge5_after = (after >= 5).sum()
n_ge3_before = (before >= 3).sum()
n_ge3_after = (after >= 3).sum()

print(f"\nCountries (in the 102-country sample) with >=5 same-country unique URLs:")
print(f"  Before hand-coded additions (ccTLD only): {n_ge5_before}")
print(f"  After hand-coded additions: {n_ge5_after}")
print(f"\nCountries with >=3 same-country unique URLs:")
print(f"  Before: {n_ge3_before}   After: {n_ge3_after}")

newly_qualifying_5 = sorted(set(after[after >= 5].index) - set(before[before >= 5].index))
print(f"\nCountries newly reaching >=5 because of the hand-coded additions: {newly_qualifying_5}")
changed = pd.DataFrame({"ISO3": before.index, "before": before.values, "after": after.values})
changed = changed[changed["before"] != changed["after"]].sort_values("after", ascending=False)
print(f"\nAll countries where the count changed at all (n={len(changed)}):")
print(changed.to_string(index=False))
changed.to_csv(OUT_DIR / "domestic_outlet_counts_before_after_handcode.csv", index=False)
print(f"\nWrote {OUT_DIR / 'domestic_outlet_counts_before_after_handcode.csv'}")

# save the summary and failures
summary = pd.DataFrame(summary_rows)
summary.to_csv(OUT_DIR / "summary_table2.csv", index=False)
print(f"\n\nWrote {len(summary)} rows to {OUT_DIR / 'summary_table2.csv'}")
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
print("outputs_v5 FOLLOW-UP COMPLETE")
print("=" * 70)
