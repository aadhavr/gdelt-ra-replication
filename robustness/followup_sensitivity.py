# more gap checks: impute-145 split into two sub-scenarios, gdelt 2.0 per-day counts
# for the gap, and the gap adjustment shown country by country
# reads: data/input/, data/intermediate/, the 26 gap-day zips in data/raw/, network
# writes: outputs/sensitivity/ (follow-up summary, gap adjustment by country, log)
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

# sub-scenarios: (1) the 3 outliers only, (2) the 7 no-article countries only
import csv
import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from lifelines import CoxPHFitter

np.random.seed(42)

OUT_DIR = config.OUT_SENSITIVITY
LOG_PATH = OUT_DIR / "followup_log.txt"


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
print("FOLLOW-UP: split impute scenarios, GDELT 2.0 per-day counts, per-country gap adjustment")
print("=" * 70)

OUTLIERS_3 = ["CAF", "VUT", "KAZ"]
NO_ARTICLE_7 = ["TUN", "GEO", "BDI", "BOL", "MRT", "DZA", "GNB"]
IMPUTE_DAYS = 145.0

# base data (same as sensitivity_analysis.py)
df = pd.read_csv(config.ODA_DATA)
df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()
df["us_oda_disbursements"] = df["us_oda_disbursements"].astype(str).str.replace(",", "")
df["us_oda_disbursements"] = pd.to_numeric(df["us_oda_disbursements"], errors="coerce")
df["days_to_first_article"] = pd.to_numeric(df["days_to_first_article"], errors="coerce")
df["log_disbursements"] = np.where(df["us_oda_disbursements"] > 0, np.log(df["us_oda_disbursements"]), np.nan)

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

usaid_unique = m.groupby("iso3")["col_57"].nunique().reset_index().rename(
    columns={"iso3": "ISO3", "col_57": "usaid_articles_unique"})
denom = pd.read_csv(config.TOTAL_UNIQUE_URL)
df = df.merge(usaid_unique, on="ISO3", how="left")
df = df.merge(denom, on="ISO3", how="left")
df["usaid_articles_unique"] = df["usaid_articles_unique"].fillna(0)

rows = []
def add(scenario, model, n, est, se_type, se, p):
    rows.append({"scenario": scenario, "model": model, "N": n, "estimate": est, "SE type": se_type, "SE": se, "p": p})

def ols_pair(scenario, label, formula, data, coef="log_disbursements"):
    mc = smf.ols(formula, data=data).fit()
    mr = smf.ols(formula, data=data).fit(cov_type="HC3")
    add(scenario, label, int(mc.nobs), mc.params[coef], "classical", mc.bse[coef], mc.pvalues[coef])
    add(scenario, label, int(mr.nobs), mr.params[coef], "HC3", mr.bse[coef], mr.pvalues[coef])

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
    add(scenario, f"{label} (HR={hr:.4f})", len(surv), coef, "Cox model-based", se, p)

# impute-145 split into two sub-scenarios
print("\n" + "-" * 70)
print("PART 1a: impute 145 for the 3 outliers only (CAF, VUT, KAZ); 7 no-article countries stay censored")
print("-" * 70)
df_a = df.copy()
df_a.loc[df_a["ISO3"].isin(OUTLIERS_3), "days_to_first_article"] = IMPUTE_DAYS
df_a["log_days"] = np.log1p(df_a["days_to_first_article"])
print(f"N with valid aid: {df_a['log_disbursements'].notna().sum()}  "
      f"(unchanged from baseline N=100, since these 3 already had an observed day value)")

ols_pair("impute-outliers-3", "days ~ aid", "log_days ~ log_disbursements", df_a)
ols_pair("impute-outliers-3", "days ~ aid + volume", "log_days ~ log_disbursements + log_total_articles", df_a)
run_cox("impute-outliers-3", "Cox: days ~ aid, no volume", df_a)
run_cox("impute-outliers-3", "Cox: days ~ aid + volume", df_a, extra_cols=["log_total_articles"])

print("\n" + "-" * 70)
print("PART 1b: impute 145 for the 7 no-article countries only; 3 outliers stay at their observed values")
print("-" * 70)
df_b = df.copy()
df_b.loc[df_b["ISO3"].isin(NO_ARTICLE_7), "days_to_first_article"] = IMPUTE_DAYS
df_b["log_days"] = np.log1p(df_b["days_to_first_article"])
n_now = df_b["log_disbursements"].notna().sum()
print(f"N with valid aid: {n_now}  (rises from baseline days-model N=93 to {n_now}, "
      f"since these 7 were previously censored/excluded, now have a value)")

ols_pair("impute-noarticle-7", "days ~ aid", "log_days ~ log_disbursements", df_b)
ols_pair("impute-noarticle-7", "days ~ aid + volume", "log_days ~ log_disbursements + log_total_articles", df_b)
run_cox("impute-noarticle-7", "Cox: days ~ aid, no volume", df_b)
run_cox("impute-noarticle-7", "Cox: days ~ aid + volume", df_b, extra_cols=["log_total_articles"])

# gdelt 2.0 per-day entry counts, 2025-06-14 to 2025-07-01
print("\n" + "-" * 70)
print("PART 2: GDELT 2.0 master file list -- entry count per day, 2025-06-14 to 2025-07-01")
print("-" * 70)
import requests

target_days = [f"202506{str(d).zfill(2)}" for d in range(14, 31)] + ["20250701"]
day_counts = {d: 0 for d in target_days}
try:
    r = requests.get("http://data.gdeltproject.org/gdeltv2/masterfilelist.txt", timeout=(10, 60), stream=True)
    print(f"masterfilelist.txt status: {r.status_code}")
    if r.status_code == 200:
        n_lines = 0
        for line in r.iter_lines(decode_unicode=True):
            n_lines += 1
            if not line:
                continue
            # gdelt 2.0 file names start with a 14-digit timestamp (yyyymmddhhmmss),
            # so take the date from the start of the file name
            parts = line.split("/")
            fname = parts[-1] if parts else line
            date_prefix = fname[:8]
            if date_prefix in day_counts:
                day_counts[date_prefix] += 1
        print(f"Lines scanned: {n_lines}")
    else:
        print("Could not fetch GDELT 2.0 master file list.")
except Exception as e:
    print(f"GDELT 2.0 check failed: {e}")

print("\nDay          GDELT 2.0 file entries")
for d in target_days:
    dt = datetime.strptime(d, "%Y%m%d").strftime("%Y-%m-%d")
    print(f"{dt}   {day_counts[d]}")
print("\n(A normal full day has up to 288 entries: 96 fifteen-minute intervals x 3 file types")
print(" [export, mentions, gkg]. Compare each day's count to that ceiling.)")
print("\nthis step only reads the gdelt 2.0 file index, it downloads no event files.")

# gap-volume adjustment, country by country
print("\n" + "-" * 70)
print("PART 3: gap-volume adjustment, shown per country (not pooled)")
print("-" * 70)
print("Neighbor windows per country: 2025-06-01..06-13 and 2025-07-02..07-14 (26 days total),")
print("own unique-URL rate x 18 missing days = that country's own estimated gap volume.")

NEIGHBOR_DAYS = (
    [datetime(2025, 6, d) for d in range(1, 14)] +
    [datetime(2025, 7, d) for d in range(2, 15)]
)


def iter_rows_from_zip(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if not names:
            return
        with zf.open(names[0], "r") as f:
            txt = io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline="")
            reader = csv.reader(txt, delimiter="\t")
            for row in reader:
                yield row


neighbor_country_urls = {}
for d in NEIGHBOR_DAYS:
    zip_path = config.GDELT_DIR / f"{d.strftime('%Y%m%d')}.export.CSV.zip"
    if not zip_path.exists():
        print(f"  warning: neighbor file missing, skipped: {zip_path.name}")
        continue
    for row in iter_rows_from_zip(zip_path):
        if len(row) <= 57:
            continue
        fips = row[51].strip().upper()
        iso3 = fips_to_iso3.get(fips)
        if iso3 is None:
            continue
        url = row[57]
        if not url:
            continue
        neighbor_country_urls.setdefault(iso3, set()).add(url)

neighbor_total = pd.DataFrame(
    [{"ISO3": k, "neighbor_total_unique": len(v)} for k, v in neighbor_country_urls.items()]
)
neighbor_matched = m[m["date_dt"].isin(NEIGHBOR_DAYS)]
neighbor_usaid = neighbor_matched.groupby("iso3")["col_57"].nunique().reset_index().rename(
    columns={"iso3": "ISO3", "col_57": "neighbor_usaid_unique"})

df_gap = df.merge(neighbor_total, on="ISO3", how="left").merge(neighbor_usaid, on="ISO3", how="left")
df_gap["neighbor_total_unique"] = df_gap["neighbor_total_unique"].fillna(0)
df_gap["neighbor_usaid_unique"] = df_gap["neighbor_usaid_unique"].fillna(0)

GAP_DAYS = 18
df_gap["est_gap_total"] = df_gap["neighbor_total_unique"] / 26.0 * GAP_DAYS
df_gap["est_gap_usaid"] = df_gap["neighbor_usaid_unique"] / 26.0 * GAP_DAYS
df_gap["total_articles_adj"] = df_gap["total_articles_unique_url"] + df_gap["est_gap_total"]
df_gap["usaid_articles_adj"] = df_gap["usaid_articles_unique"] + df_gap["est_gap_usaid"]
df_gap["attention_share_unique"] = df_gap["usaid_articles_unique"] / df_gap["total_articles_unique_url"]
df_gap["attention_share_adj"] = df_gap["usaid_articles_adj"] / df_gap["total_articles_adj"]
df_gap["pct_change"] = (df_gap["attention_share_adj"] / df_gap["attention_share_unique"] - 1) * 100

cols_to_show = ["ISO3", "country", "neighbor_total_unique", "est_gap_total", "total_articles_unique_url",
                "neighbor_usaid_unique", "est_gap_usaid", "usaid_articles_unique",
                "attention_share_unique", "attention_share_adj", "pct_change"]
country_table = df_gap[cols_to_show].sort_values("pct_change", ascending=False)
country_table.to_csv(OUT_DIR / "gap_adjustment_by_country.csv", index=False)
print(f"\nWrote per-country gap adjustment table: {OUT_DIR / 'gap_adjustment_by_country.csv'}  (N={len(country_table)})")
print("\nTop 10 countries by percent change in attention_share from the gap adjustment:")
print(country_table.head(10).to_string(index=False))
print("\nBottom 10 (smallest/most negative change):")
print(country_table.tail(10).to_string(index=False))
print(f"\nMedian absolute percent change across all {len(country_table)} countries: "
      f"{country_table['pct_change'].abs().median():.3f}%")
print(f"Max absolute percent change: {country_table['pct_change'].abs().max():.3f}% "
      f"({country_table.loc[country_table['pct_change'].abs().idxmax(), 'ISO3']})")

# run the attention model again on the adjusted share, for reference
ols_pair("gap-adjusted-percountry", "attention ~ aid (country-specific gap-adjusted)",
          "log_attention_share_adj ~ log_disbursements",
          df_gap.assign(log_attention_share_adj=np.log1p(df_gap["attention_share_adj"])))

# save
summary = pd.DataFrame(rows)
summary.to_csv(OUT_DIR / "followup_summary_table.csv", index=False)
print(f"\n\nWrote {len(summary)} rows to {OUT_DIR / 'followup_summary_table.csv'}")
print(summary.to_string(index=False))
print("\n" + "=" * 70)
print("FOLLOW-UP COMPLETE")
print("=" * 70)
