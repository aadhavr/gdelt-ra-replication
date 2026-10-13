# exploratory: avgtone and goldstein of the matched rows vs log aid (not in the paper)
# reads: data/intermediate/ (matched rows, unique url totals),
#   data/input/3-29-v2_oda_data.csv and data/input/country-codes.csv
# writes: results.csv, descriptives.csv and log.txt in this folder
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

# import config.py from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

OUT = Path(__file__).resolve().parent

# gdelt 1.0 column positions in matches_rows.csv
COLS = {"col_0": "globaleventid", "col_30": "goldstein", "col_34": "avgtone",
        "col_51": "fips", "col_57": "url"}
OUTCOMES = ["avgtone", "goldstein"]
MIN_URLS = 5  # cutoff for m4


class Tee:  # copy everything printed to log.txt
    def __init__(self, path):
        self.file = open(path, "w")
        self.stdout = sys.stdout

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


sys.stdout = Tee(OUT / "log.txt")
print("exploratory: tone and goldstein vs log aid")

# matched rows -> iso3, same mapping as build_all.py
cc = pd.read_csv(config.COUNTRY_CODES, dtype=str)
cc["FIPS"] = cc["FIPS"].astype(str).str.strip().str.upper()
fips_to_iso3 = dict(zip(cc["FIPS"], cc["ISO3166-1-Alpha-3"]))

m = pd.read_csv(config.MATCHES_ROWS, dtype=str, low_memory=False)[list(COLS)].rename(columns=COLS)
print(f"matched rows: {len(m)}")
m["iso3"] = m["fips"].astype(str).str.strip().str.upper().map(fips_to_iso3)
m = m.dropna(subset=["iso3"])
print(f"matched rows with an iso3 country: {len(m)}")
for c in OUTCOMES:
    m[c] = pd.to_numeric(m[c], errors="coerce")
print(f"rows with missing avgtone: {m['avgtone'].isna().sum()}, missing goldstein: {m['goldstein'].isna().sum()}")

# url level: one row per (country, url), mean over its rows
urls = m.groupby(["iso3", "url"], as_index=False).agg(
    avgtone=("avgtone", "mean"), goldstein=("goldstein", "mean"), n_rows=("url", "size"))
print(f"unique urls within country: {len(urls)} (unique urls overall: {m['url'].nunique()})")

# country level: mean over urls, and the event-level version (mean over unique event ids)
ctry = urls.groupby("iso3").agg(n_urls=("url", "size"), mean_avgtone=("avgtone", "mean"),
                                mean_goldstein=("goldstein", "mean"))
events = m.drop_duplicates(["iso3", "globaleventid"])
print(f"unique event ids within country: {len(events)}")
ev = events.groupby("iso3").agg(n_events=("globaleventid", "size"), ev_avgtone=("avgtone", "mean"),
                                ev_goldstein=("goldstein", "mean"))
ctry = ctry.join(ev)
print(f"countries with at least one matched url: {len(ctry)}")

# log aid as in table 3, log total unique articles as in the volume control
aid = pd.read_csv(config.ODA_DATA)
aid["ISO3"] = aid["ISO3"].astype(str).str.strip().str.upper()
aid["us_oda_disbursements"] = pd.to_numeric(aid["us_oda_disbursements"].astype(str).str.replace(",", ""), errors="coerce")
aid["log_aid"] = np.log(aid["us_oda_disbursements"].where(aid["us_oda_disbursements"] > 0))
tu = pd.read_csv(config.TOTAL_UNIQUE_URL)
tu["log_total_articles"] = np.log(tu["total_articles_unique_url"].where(tu["total_articles_unique_url"] > 0))
print(f"countries in the aid file: {len(aid)}")

# n_urls for all 102 sample countries (0 = no matched url), for the count description
all102 = aid[["ISO3"]].join(ctry["n_urls"], on="ISO3")
all102["n_urls"] = all102["n_urls"].fillna(0).astype(int)

df = aid[["ISO3", "country", "log_aid"]].join(ctry, on="ISO3", how="inner")
print(f"sample countries with at least one matched url: {len(df)}")
df = df.dropna(subset=["log_aid"])
print(f"... and a valid aid value (> 0): {len(df)}")
df = df.merge(tu[["ISO3", "log_total_articles"]], on="ISO3", how="left")
print(f"... with log total unique articles: {df['log_total_articles'].notna().sum()}")

# descriptives
rows = []
for col, label in [("mean_avgtone", "avgtone, country mean over urls"),
                   ("mean_goldstein", "goldstein, country mean over urls"),
                   ("ev_avgtone", "avgtone, country mean over events"),
                   ("ev_goldstein", "goldstein, country mean over events")]:
    s = df[col]
    rows.append({"measure": label, "N": s.notna().sum(), "mean": s.mean(), "sd": s.std(), "min": s.min(), "max": s.max()})
for name, s in [("n_urls, analysis sample", df["n_urls"]), ("n_urls, all 102 countries (0 = none)", all102["n_urls"])]:
    rows.append({"measure": name, "N": len(s), "mean": s.mean(), "sd": s.std(), "min": s.min(), "max": s.max(),
                 "p25": s.quantile(0.25), "median": s.median(), "p75": s.quantile(0.75),
                 "n_lt_5": int((s < 5).sum()), "n_ge_5": int((s >= 5).sum())})
desc = pd.DataFrame(rows)
desc.to_csv(OUT / "descriptives.csv", index=False)
print("\ndescriptives:\n" + desc.to_string(index=False))

# models (hc3 unless stated)
res = []


def add(outcome, model, fit, se_type, n):
    res.append({"outcome": outcome, "model": model, "N": n, "beta_hat": fit.params["log_aid"],
                "se_type": se_type, "se": fit.bse["log_aid"], "p": fit.pvalues["log_aid"], "r2": fit.rsquared})


url_df = urls.merge(df[["ISO3", "log_aid"]], left_on="iso3", right_on="ISO3", how="inner")
print(f"\nurl-level rows (urls in sample countries): {len(url_df)}, countries: {url_df['iso3'].nunique()}")

for o in OUTCOMES:
    y = f"mean_{o}"
    d1 = df.dropna(subset=[y, "log_aid"])
    add(o, "m1: outcome ~ log_aid", smf.ols(f"{y} ~ log_aid", d1).fit(cov_type="HC3"), "HC3", len(d1))
    d2 = df.dropna(subset=[y, "log_aid", "log_total_articles"])
    add(o, "m2: + log_total_articles", smf.ols(f"{y} ~ log_aid + log_total_articles", d2).fit(cov_type="HC3"), "HC3", len(d2))
    add(o, "m3: m1 weighted by n_urls (wls)", smf.wls(f"{y} ~ log_aid", d1, weights=d1["n_urls"]).fit(cov_type="HC3"),
        "HC3", len(d1))
    d4 = d1[d1["n_urls"] >= MIN_URLS]
    add(o, f"m4: m1, n_urls >= {MIN_URLS}", smf.ols(f"{y} ~ log_aid", d4).fit(cov_type="HC3"), "HC3", len(d4))
    d5 = url_df.dropna(subset=[o, "log_aid"])
    groups = pd.factorize(d5["iso3"])[0]
    add(o, "m5: url level", smf.ols(f"{o} ~ log_aid", d5).fit(cov_type="cluster", cov_kwds={"groups": groups}),
        f"cluster by country ({d5['iso3'].nunique()})", len(d5))
    ye = f"ev_{o}"
    de = df.dropna(subset=[ye, "log_aid"])
    add(o, "robustness: m1, event level", smf.ols(f"{ye} ~ log_aid", de).fit(cov_type="HC3"), "HC3", len(de))

out = pd.DataFrame(res)
out.to_csv(OUT / "results.csv", index=False)
show = out.copy()
for c in ["beta_hat", "se", "p", "r2"]:
    show[c] = show[c].map(lambda v: f"{v:.4f}")
print("\nresults:\n" + show.to_string(index=False))
print("\nsign vs predictions.md: dampening predicts beta_hat > 0 for both outcomes; salience makes no prediction.")
for _, r in out.iterrows():
    print(f"  {r['outcome']:9s} {r['model']:32s} beta_hat {r['beta_hat']:+.4f} -> "
          f"{'positive, same sign as the dampening prediction' if r['beta_hat'] > 0 else 'negative, opposite to the dampening prediction'}")
print(f"\nfiles written to {OUT.relative_to(config.ROOT)}/")
