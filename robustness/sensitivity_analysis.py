# tests how much the 18 missing gdelt days (2025-06-14 to 2025-07-01) could move the
# results: an impute-145 and a drop scenario, a neighbor-day adjustment, a gdelt 2.0 check
# reads: data/input/, data/intermediate/, the 26 gap-day zips in data/raw/, network
# writes: outputs/sensitivity/ (summary table and log)
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

# the gap files do not exist at gdelt, so this script does not try to download them
import csv
import io
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from lifelines import CoxPHFitter

np.random.seed(42)

OUT_DIR = config.OUT_SENSITIVITY
OUT_DIR.mkdir(exist_ok=True)
LOG_PATH = OUT_DIR / "log.txt"


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
print("SENSITIVITY ANALYSIS: MISSING GDELT FILES, 2025-06-14 to 2025-07-01")
print("=" * 70)

EXPOSED_14 = ["TUN", "GEO", "BDI", "BOL", "MRT", "DZA", "GNB",
              "SVK", "KAZ", "VUT", "SWZ", "CAF", "BGR", "MLT"]
IMPUTE_DAYS = 145.0

# base data
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

# unique-url numerator (usaid-matched rows) and denominator (all gdelt rows)
m = pd.read_csv(config.MATCHES_ROWS, dtype=str, low_memory=False)
cc_raw = pd.read_csv(config.COUNTRY_CODES, dtype=str)
cc_raw["FIPS"] = cc_raw["FIPS"].astype(str).str.strip().str.upper()
fips_to_iso3 = dict(zip(cc_raw["FIPS"], cc_raw["ISO3166-1-Alpha-3"]))
m["iso3"] = m["col_51"].astype(str).str.strip().str.upper().map(fips_to_iso3)
m = m.dropna(subset=["iso3"])
m["date_dt"] = pd.to_datetime(m["date"], format="%Y%m%d")

usaid_unique = m.groupby("iso3")["col_57"].nunique().reset_index().rename(
    columns={"iso3": "ISO3", "col_57": "usaid_articles_unique"})
denom = pd.read_csv(config.TOTAL_UNIQUE_URL)

df = df.merge(usaid_unique, on="ISO3", how="left")
df = df.merge(denom, on="ISO3", how="left")
df["usaid_articles_unique"] = df["usaid_articles_unique"].fillna(0)
df["attention_share_unique"] = df["usaid_articles_unique"] / df["total_articles_unique_url"]
df["log_attention_share_unique"] = np.log1p(df["attention_share_unique"])
df["log_total_articles_unique"] = np.log(df["total_articles_unique_url"].where(df["total_articles_unique_url"] > 0))

print(f"\nBase sample loaded: N={len(df)}")
print(f"Exposed-14 list: {EXPOSED_14}")
in_sample = df[df['ISO3'].isin(EXPOSED_14)]['ISO3'].tolist()
print(f"Of these, present in the 102-country aid sample: {in_sample}")
print(f"Not present (no aid value, irrelevant to the regressions): {[c for c in EXPOSED_14 if c not in in_sample]}")

rows = []
def add(scenario, model, n, est, se_type, se, p):
    rows.append({"scenario": scenario, "model": model, "N": n, "estimate": est, "SE type": se_type, "SE": se, "p": p})

def ols_pair(scenario, label, formula, data, coef="log_disbursements"):
    reg = data.dropna(subset=[c for c in [coef, formula.split("~")[0].strip()] if c])
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
    return cph

# baseline (unique-url), for side-by-side reference
print("\n" + "-" * 70)
print("BASELINE (original data, unique-URL attention, for reference)")
print("-" * 70)
ols_pair("baseline", "days ~ aid", "log_days ~ log_disbursements",
          df.assign(log_days=np.log1p(df["days_to_first_article"])))
ols_pair("baseline", "days ~ aid + volume", "log_days ~ log_disbursements + log_total_articles",
          df.assign(log_days=np.log1p(df["days_to_first_article"])))
ols_pair("baseline", "attention ~ aid", "log_attention_share_unique ~ log_disbursements", df)
ols_pair("baseline", "attention ~ aid + volume", "log_attention_share_unique ~ log_disbursements + log_total_articles_unique", df)
run_cox("baseline", "Cox: days ~ aid, no volume", df)
run_cox("baseline", "Cox: days ~ aid + volume", df, extra_cols=["log_total_articles"])

# scenario 1: set days_to_first_article = 145 for the exposed 14
print("\n" + "-" * 70)
print(f"SCENARIO 1: impute days_to_first_article = {IMPUTE_DAYS} for the 14 exposed countries")
print("-" * 70)
df_imp = df.copy()
df_imp.loc[df_imp["ISO3"].isin(EXPOSED_14), "days_to_first_article"] = IMPUTE_DAYS
df_imp["log_days"] = np.log1p(df_imp["days_to_first_article"])
n_newly_included = (df["ISO3"].isin(EXPOSED_14) & df["days_to_first_article"].isna() & df["log_disbursements"].notna()).sum()
print(f"Countries newly entering the days regression under imputation (were censored, now have a value): {n_newly_included}")

ols_pair("impute-145", "days ~ aid", "log_days ~ log_disbursements", df_imp)
ols_pair("impute-145", "days ~ aid + volume", "log_days ~ log_disbursements + log_total_articles", df_imp)
run_cox("impute-145", "Cox: days ~ aid, no volume", df_imp)
run_cox("impute-145", "Cox: days ~ aid + volume", df_imp, extra_cols=["log_total_articles"])

# scenario 2: drop the exposed 14
print("\n" + "-" * 70)
print("SCENARIO 2: drop the 14 exposed countries entirely")
print("-" * 70)
df_drop = df[~df["ISO3"].isin(EXPOSED_14)].copy()
df_drop["log_days"] = np.log1p(df_drop["days_to_first_article"])
print(f"N remaining after drop (full aid-valid sample): {df_drop['log_disbursements'].notna().sum()}")

ols_pair("drop-14", "days ~ aid", "log_days ~ log_disbursements", df_drop)
ols_pair("drop-14", "days ~ aid + volume", "log_days ~ log_disbursements + log_total_articles", df_drop)
run_cox("drop-14", "Cox: days ~ aid, no volume", df_drop)
run_cox("drop-14", "Cox: days ~ aid + volume", df_drop, extra_cols=["log_total_articles"])
n_censored_remaining = (df_drop["log_disbursements"].notna() & df_drop["days_to_first_article"].isna()).sum()
print(f"Censored countries remaining after drop: {n_censored_remaining} "
      f"(all 7 originally-censored countries were inside the exposed-14 list, so this should be 0)")

# scenario 3: gap-adjusted attention share from neighbor days
print("\n" + "-" * 70)
print("SCENARIO 3: attention share adjusted for estimated gap volume")
print("-" * 70)
print("Neighbor windows: 2025-06-01 to 2025-06-13 (13 days) and 2025-07-02 to 2025-07-14 (13 days) = 26 days")
print("Gap to estimate: 2025-06-14 to 2025-07-01 = 18 days")

NEIGHBOR_DAYS = (
    [datetime(2025, 6, d) for d in range(1, 14)] +
    [datetime(2025, 7, d) for d in range(2, 15)]
)
assert len(NEIGHBOR_DAYS) == 26


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
        print(f"  warning: neighbor file missing: {zip_path.name}")
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
print(f"\nNeighbor-window total unique-URL scan complete: {len(neighbor_total)} countries, 26 days.")

neighbor_matched = m[m["date_dt"].isin(NEIGHBOR_DAYS)]
neighbor_usaid = neighbor_matched.groupby("iso3")["col_57"].nunique().reset_index().rename(
    columns={"iso3": "ISO3", "col_57": "neighbor_usaid_unique"})
print(f"Neighbor-window USAID-matched unique-URL count: {len(neighbor_usaid)} countries with >=1 match, 26 days.")

df_gap = df.merge(neighbor_total, on="ISO3", how="left").merge(neighbor_usaid, on="ISO3", how="left")
df_gap["neighbor_total_unique"] = df_gap["neighbor_total_unique"].fillna(0)
df_gap["neighbor_usaid_unique"] = df_gap["neighbor_usaid_unique"].fillna(0)

GAP_DAYS = 18
df_gap["est_gap_total"] = df_gap["neighbor_total_unique"] / 26.0 * GAP_DAYS
df_gap["est_gap_usaid"] = df_gap["neighbor_usaid_unique"] / 26.0 * GAP_DAYS

df_gap["total_articles_adj"] = df_gap["total_articles_unique_url"] + df_gap["est_gap_total"]
df_gap["usaid_articles_adj"] = df_gap["usaid_articles_unique"] + df_gap["est_gap_usaid"]
df_gap["attention_share_adj"] = df_gap["usaid_articles_adj"] / df_gap["total_articles_adj"]
df_gap["log_attention_share_adj"] = np.log1p(df_gap["attention_share_adj"])
df_gap["log_total_articles_adj"] = np.log(df_gap["total_articles_adj"].where(df_gap["total_articles_adj"] > 0))

pct_change_total = (df_gap["est_gap_total"].sum() / df_gap["total_articles_unique_url"].sum()) * 100
pct_change_usaid = (df_gap["est_gap_usaid"].sum() / df_gap["usaid_articles_unique"].sum().clip(min=1)) * 100
print(f"\nEstimated gap volume as % of observed total (pooled, all countries): "
      f"total articles +{pct_change_total:.3f}%,  USAID-matched articles +{pct_change_usaid:.3f}%")
print("(USAID-matched estimate uses the exposed-14 countries' neighbor-window match rate, which is near zero")
print(" for most of them -- the 18-day gap barely moves the USAID-matched numerator in percentage terms,")
print(" but the comparison below shows whether it moves the regression result at all.)")

ols_pair("gap-adjusted", "attention ~ aid (gap-adjusted)", "log_attention_share_adj ~ log_disbursements", df_gap)
ols_pair("gap-adjusted", "attention ~ aid + volume (gap-adjusted)",
          "log_attention_share_adj ~ log_disbursements + log_total_articles_adj", df_gap)

# gdelt 2.0 check (file index only, no event files)
print("\n" + "-" * 70)
print("SCENARIO 4: does GDELT 2.0 cover 2025-06-14 to 2025-07-01? (index check only)")
print("-" * 70)
import requests

v2_found = None
try:
    r = requests.get("http://data.gdeltproject.org/gdeltv2/masterfilelist.txt", timeout=(10, 60), stream=True)
    print(f"masterfilelist.txt status: {r.status_code}")
    if r.status_code == 200:
        target_prefixes = [f"202506{str(d).zfill(2)}" for d in range(14, 31)] + ["20250701"]
        hits = {p: 0 for p in target_prefixes}
        count = 0
        for line in r.iter_lines(decode_unicode=True):
            count += 1
            for p in target_prefixes:
                if line and p in line:
                    hits[p] += 1
            if count > 4_000_000:  # safety cap
                print("  (hit safety cap scanning masterfilelist.txt, stopping early)")
                break
        total_hits = sum(hits.values())
        print(f"Lines scanned: {count}")
        print(f"Total GDELT 2.0 file entries found for 2025-06-14..2025-07-01: {total_hits}")
        missing_days = [p for p, c in hits.items() if c == 0]
        present_days = [p for p, c in hits.items() if c > 0]
        print(f"Days with >=1 GDELT 2.0 file entry: {present_days}")
        print(f"Days with zero GDELT 2.0 file entries: {missing_days}")
        v2_found = total_hits > 0
    else:
        print("Could not fetch GDELT 2.0 master file list.")
except Exception as e:
    print(f"GDELT 2.0 check failed: {e}")

print("\nthis step only reads the gdelt 2.0 file index, it downloads no event files.")

# save the summary table
summary = pd.DataFrame(rows)
summary.to_csv(OUT_DIR / "sensitivity_summary_table.csv", index=False)
print(f"\n\nWrote {len(summary)} rows to {OUT_DIR / 'sensitivity_summary_table.csv'}")
print(summary.to_string(index=False))
print("\n" + "=" * 70)
print("SENSITIVITY ANALYSIS COMPLETE")
print("=" * 70)
