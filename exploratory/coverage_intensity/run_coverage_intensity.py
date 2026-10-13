# exploratory: how widely matched events were covered vs log aid (not in the paper)
# reads: data/input/ (aid data, country codes), data/intermediate/ (matched rows, totals)
# writes: results.csv and log.txt in this folder
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

# import config.py from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

OUT = Path(__file__).resolve().parent
FIELDS = {"col_31": "nummentions", "col_32": "numsources", "col_33": "numarticles"}  # gdelt 1.0 positions
MIN_URLS = 5  # cutoff for i4


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
print("exploratory: coverage intensity")

# base data, lines copied from build_all.py
df = pd.read_csv(config.ODA_DATA)
print(f"aid file: N = {len(df)}")
df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()
df["us_oda_disbursements"] = df["us_oda_disbursements"].astype(str).str.replace(",", "")
df["us_oda_disbursements"] = pd.to_numeric(df["us_oda_disbursements"], errors="coerce")
df["days_to_first_article"] = pd.to_numeric(df["days_to_first_article"], errors="coerce")
df["log_days"] = np.log1p(df["days_to_first_article"])
df["log_disbursements"] = np.log(df["us_oda_disbursements"].where(df["us_oda_disbursements"] > 0))

cc_raw = pd.read_csv(config.COUNTRY_CODES, dtype=str)
cc_raw["FIPS"] = cc_raw["FIPS"].astype(str).str.strip().str.upper()
fips_to_iso3 = dict(zip(cc_raw["FIPS"], cc_raw["ISO3166-1-Alpha-3"]))
m = pd.read_csv(config.MATCHES_ROWS, dtype=str, low_memory=False)
print(f"matched rows: {len(m)}")
m["iso3"] = m["col_51"].astype(str).str.strip().str.upper().map(fips_to_iso3)
m = m.dropna(subset=["iso3"])
print(f"matched rows with an iso3 country: {len(m)}")
usaid_unique = m.groupby("iso3")["col_57"].nunique().reset_index().rename(
    columns={"iso3": "ISO3", "col_57": "usaid_articles_unique"})
df = df.merge(usaid_unique, on="ISO3", how="left")
df["usaid_articles_unique"] = df["usaid_articles_unique"].fillna(0)
denom = pd.read_csv(config.TOTAL_UNIQUE_URL)
df = df.merge(denom, on="ISO3", how="left")
df["log_total_articles_unique"] = np.log(df["total_articles_unique_url"].where(df["total_articles_unique_url"] > 0))
df["attention_share_unique"] = df["usaid_articles_unique"] / df["total_articles_unique_url"]
df["log_attention_share_unique"] = np.log1p(df["attention_share_unique"])

# baseline check: table 3 and the unique-url attention model must match the paper values
b3 = smf.ols("log_days ~ log_disbursements", df).fit(cov_type="HC3")
b4 = smf.ols("log_attention_share_unique ~ log_disbursements", df).fit(cov_type="HC3")
got = (round(b3.params["log_disbursements"], 4), int(b3.nobs), round(b3.bse["log_disbursements"], 4),
       round(b4.params["log_disbursements"] * 1000, 3), int(b4.nobs), round(b4.pvalues["log_disbursements"], 4))
want = (-0.1695, 93, 0.0551, 0.224, 100, 0.0002)
print(f"baseline: table 3 beta_hat {got[0]}, N {got[1]}, hc3 se {got[2]}; "
      f"attention (per 1,000) beta_hat {got[3]}, N {got[4]}, hc3 p {got[5]}")
if got != want:
    sys.exit(f"baseline does not match. expected {want}, got {got}")
print("baseline matches")

# distribution of the raw fields first (they are very skewed)
for c in FIELDS:
    m[c] = pd.to_numeric(m[c], errors="coerce")
q = [0, 0.01, 0.25, 0.5, 0.75, 0.9, 0.99, 1]
dist = pd.DataFrame({FIELDS[c]: m[c].quantile(q).values for c in FIELDS}, index=[f"p{int(x*100)}" for x in q])
dist.loc["mean"] = [m[c].mean() for c in FIELDS]
dist.loc["skewness"] = [m[c].skew() for c in FIELDS]
print(f"\nrow-level distribution (N = {len(m)} rows):\n{dist.round(2).to_string()}")

# unique (country, url) pairs, mean per pair, then mean over a country's pairs
pairs = m.groupby(["iso3", "col_57"], as_index=False)[list(FIELDS)].mean()
print(f"\nunique (country, url) pairs: {len(pairs)}")
ctry = pairs.groupby("iso3")[list(FIELDS)].mean().rename(columns=FIELDS)
ctry["n_urls"] = pairs.groupby("iso3").size()
for f in FIELDS.values():
    ctry[f"log_{f}"] = np.log(ctry[f])

# table 3 sample: days and valid aid
d = df.dropna(subset=["log_days", "log_disbursements"]).join(ctry, on="ISO3", how="inner")
print(f"table 3 sample with matched urls: N = {len(d)}")
cdist = d[list(FIELDS.values()) + [f"log_{f}" for f in FIELDS.values()] + ["n_urls"]].describe(
    percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]).T
cdist["skewness"] = d[cdist.index].skew()
print(f"\ncountry-level distribution (N = {len(d)}):\n{cdist.round(3).to_string()}")
print(f"countries with n_urls >= {MIN_URLS}: {(d['n_urls'] >= MIN_URLS).sum()}")

res = []
for f in FIELDS.values():
    y = f"log_{f}"
    specs = [("i1: plain", smf.ols(f"{y} ~ log_disbursements", d)),
             ("i2: + log_total_articles", smf.ols(f"{y} ~ log_disbursements + log_total_articles_unique", d)),
             ("i3: weighted by n_urls (wls)", smf.wls(f"{y} ~ log_disbursements", d, weights=d["n_urls"])),
             (f"i4: n_urls >= {MIN_URLS}", smf.ols(f"{y} ~ log_disbursements", d[d["n_urls"] >= MIN_URLS]))]
    for name, mod in specs:
        r = mod.fit(cov_type="HC3")
        res.append({"outcome": f"log mean {f}", "model": name, "N": int(r.nobs),
                    "beta_hat": r.params["log_disbursements"], "se_type": "HC3",
                    "se": r.bse["log_disbursements"], "p": r.pvalues["log_disbursements"], "r2": r.rsquared})

out = pd.DataFrame(res)
out.to_csv(OUT / "results.csv", index=False)
show = out.copy()
for c in ["beta_hat", "se", "p", "r2"]:
    show[c] = show[c].map(lambda v: f"{v:.4f}")
print("\nresults:\n" + show.to_string(index=False))
print(f"\nmodels run: {len(out)}")
print(f"files written to {OUT.relative_to(config.ROOT)}/")
