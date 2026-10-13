# exploratory: does the aid slope change with v-dem press freedom? (not in the paper)
# reads: data/input/ (aid data, country codes, vdem_filtered.csv or --vdem <file>)
#   and data/intermediate/ (matched rows, unique url totals)
# writes: results.csv and log.txt in this folder
# writes: results.csv and log.txt in this folder
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as sstats

# import config.py from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

OUT = Path(__file__).resolve().parent
MODERATORS = {"v2mecenefm": "a: censorship effort (high = less censorship)",
              "v2meharjrn": "b: journalist harassment (high = less harassment)"}


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


ap = argparse.ArgumentParser()
ap.add_argument("--vdem", default=str(config.VDEM_FILTERED), help="path to vdem_filtered.csv")
args = ap.parse_args()
vdem_path = Path(args.vdem)
if not vdem_path.exists():
    sys.exit("error: vdem_filtered.csv not found.\n"
             "put it in data/input/vdem_filtered.csv (make it with: python src/00_filter_vdem.py,\n"
             "from the v-dem v12 country-year core csv, see the readme), or run this script with\n"
             "--vdem <path to vdem_filtered.csv>.")

sys.stdout = Tee(OUT / "log.txt")
print("exploratory: press freedom interaction")
print(f"v-dem file: {vdem_path.name}")

# base data, lines copied from build_all.py
df = pd.read_csv(config.ODA_DATA)
print(f"aid file: N = {len(df)}")
df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()
df["us_oda_disbursements"] = df["us_oda_disbursements"].astype(str).str.replace(",", "")
df["us_oda_disbursements"] = pd.to_numeric(df["us_oda_disbursements"], errors="coerce")
df["days_to_first_article"] = pd.to_numeric(df["days_to_first_article"], errors="coerce")
df["log_days"] = np.log1p(df["days_to_first_article"])
df["log_disbursements"] = np.log(df["us_oda_disbursements"].where(df["us_oda_disbursements"] > 0))
print(f"N with days: {df['days_to_first_article'].notna().sum()}, N with valid aid: {df['log_disbursements'].notna().sum()}")

cc_raw = pd.read_csv(config.COUNTRY_CODES, dtype=str)
cc_raw["FIPS"] = cc_raw["FIPS"].astype(str).str.strip().str.upper()
fips_to_iso3 = dict(zip(cc_raw["FIPS"], cc_raw["ISO3166-1-Alpha-3"]))
m = pd.read_csv(config.MATCHES_ROWS, dtype=str, low_memory=False)
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
print(f"N with unique-url attention share: {df['attention_share_unique'].notna().sum()}")

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

# v-dem moderators, 2018-2022 window as in tables 5 and 6
vdem = pd.read_csv(vdem_path)
vdem_window = vdem[vdem["year"].between(2018, 2022)]
print(f"v-dem rows in 2018-2022: {len(vdem_window)}, years present: {sorted(vdem_window['year'].unique().tolist())}")
vdem_avg = vdem_window.groupby("country_text_id", as_index=False)[list(MODERATORS)].mean()
vdem_avg = vdem_avg.rename(columns={"country_text_id": "ISO3"})
df = df.merge(vdem_avg, on="ISO3", how="left")
for mod in MODERATORS:
    print(f"N with {mod}: {df[mod].notna().sum()}")

OUTCOMES = {"log_days": ("days (log 1+days)", 1.0),
            "log_attention_share_unique": ("attention, unique url (per 1,000)", 1000.0)}
res = []


def add(outcome, model, n, b, se_type, se, p, r2):
    res.append({"outcome": outcome, "model": model, "N": n, "beta_hat": b, "se_type": se_type,
                "se": se, "p": p, "r2": r2})


for y, (ylab, scale) in OUTCOMES.items():
    for mod, mlab in MODERATORS.items():
        d = df[[y, "log_disbursements", mod, "log_total_articles_unique"]].dropna().copy()
        d["mod_c"] = d[mod] - d[mod].mean()  # centered at the sample mean
        q10, q90 = d["mod_c"].quantile(0.10), d["mod_c"].quantile(0.90)
        print(f"\n{ylab} | moderator {mlab}: N = {len(d)}, mean = {d[mod].mean():.4f}, "
              f"p10 = {d[mod].quantile(0.10):.4f}, p90 = {d[mod].quantile(0.90):.4f}")
        for name, rhs in [("p1", "log_disbursements * mod_c"),
                          ("p2", "log_disbursements * mod_c + log_total_articles_unique")]:
            f = smf.ols(f"{y} ~ {rhs}", d).fit(cov_type="HC3")
            tag = f"{name}, moderator {mlab}"
            add(ylab, f"{tag}: aid at mean moderator", int(f.nobs), f.params["log_disbursements"] * scale, "HC3",
                f.bse["log_disbursements"] * scale, f.pvalues["log_disbursements"], f.rsquared)
            add(ylab, f"{tag}: aid x moderator", int(f.nobs), f.params["log_disbursements:mod_c"] * scale, "HC3",
                f.bse["log_disbursements:mod_c"] * scale, f.pvalues["log_disbursements:mod_c"], f.rsquared)
            # aid slope at the 10th and 90th percentile, same math as table 9
            cov = f.cov_params()
            b_aid, b_int = f.params["log_disbursements"], f.params["log_disbursements:mod_c"]
            v_aid = cov.loc["log_disbursements", "log_disbursements"]
            v_int = cov.loc["log_disbursements:mod_c", "log_disbursements:mod_c"]
            c_ai = cov.loc["log_disbursements", "log_disbursements:mod_c"]
            for qname, a in [("p10", q10), ("p90", q90)]:
                eff = b_aid + b_int * a
                se = np.sqrt(v_aid + a ** 2 * v_int + 2 * a * c_ai)
                p = 2 * (1 - sstats.t.cdf(abs(eff / se), f.df_resid))
                add(ylab, f"{tag}: aid slope at moderator {qname}", int(f.nobs), eff * scale,
                    "HC3 (t, df resid)", se * scale, p, f.rsquared)
            print(f"  {name}: aid {f.params['log_disbursements']*scale:+.4f} (p {f.pvalues['log_disbursements']:.4f}), "
                  f"aid x moderator {f.params['log_disbursements:mod_c']*scale:+.4f} "
                  f"(p {f.pvalues['log_disbursements:mod_c']:.4f}), N {int(f.nobs)}")

out = pd.DataFrame(res)
out.to_csv(OUT / "results.csv", index=False)
show = out.copy()
for c in ["beta_hat", "se", "p", "r2"]:
    show[c] = show[c].map(lambda v: f"{v:.4f}")
print("\nresults:\n" + show.to_string(index=False))
print(f"\nmodels run: {len(out) // 4} (each gives 4 rows: aid at mean, interaction, slope at p10, slope at p90)")
print(f"files written to {OUT.relative_to(config.ROOT)}/")
