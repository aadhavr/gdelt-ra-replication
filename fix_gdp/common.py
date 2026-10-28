# gdp fix: shared loader and model helpers, lines copied from gross_aid/run_gross_aid.py and followup
# reads: data/input/ (aid data, country codes, wdi snapshot), data/intermediate/ (matched rows,
#   unique url totals, aid_gross_2018_2022.csv)
# writes: nothing
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.dont_write_bytecode = True

# paths copied from config.py (not imported: importing it makes folders under outputs/)
ROOT = Path(__file__).resolve().parents[1]
ODA_DATA = ROOT / "data" / "input" / "3-29-v2_oda_data.csv"
COUNTRY_CODES = ROOT / "data" / "input" / "country-codes.csv"
WDI_SNAPSHOT = ROOT / "data" / "input" / "wdi_population_gdp.csv"
MATCHES_ROWS = ROOT / "data" / "intermediate" / "usaid_closure_v1" / "matches_rows.csv"
TOTAL_UNIQUE_URL = ROOT / "data" / "intermediate" / "total_articles_unique_url.csv"
GROSS_FILE = ROOT / "data" / "intermediate" / "aid_gross_2018_2022.csv"
OUT = ROOT / "outputs" / "gdp_fix"

DAYS, ATTN = "log_days", "log_attention_share_unique"
OUTCOMES = [(DAYS, 1), (ATTN, 1000)]  # attention beta and se per 1,000, as in gross_aid


def out_path(name):
    # never overwrite an existing output
    p = OUT / name
    if p.exists():
        sys.exit(f"STOP: {p.relative_to(ROOT)} exists, not overwriting.")
    return p


def load(gdp=None):
    # lines copied from gross_aid/run_gross_aid.py load(); gdp: optional (ISO3, gdp_avg) frame that replaces
    # the snapshot gdp_avg
    df = pd.read_csv(ODA_DATA)
    df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()
    df["us_oda_disbursements"] = df["us_oda_disbursements"].astype(str).str.replace(",", "")
    df["us_oda_disbursements"] = pd.to_numeric(df["us_oda_disbursements"], errors="coerce")
    df["days_to_first_article"] = pd.to_numeric(df["days_to_first_article"], errors="coerce")
    df["log_days"] = np.log1p(df["days_to_first_article"])
    df["log_disbursements"] = np.where(df["us_oda_disbursements"] > 0, np.log(df["us_oda_disbursements"]), np.nan)

    cc_raw = pd.read_csv(COUNTRY_CODES, dtype=str)
    cc_raw["FIPS"] = cc_raw["FIPS"].astype(str).str.strip().str.upper()
    fips_to_iso3 = dict(zip(cc_raw["FIPS"], cc_raw["ISO3166-1-Alpha-3"]))
    m = pd.read_csv(MATCHES_ROWS, dtype=str, low_memory=False)
    m["iso3"] = m["col_51"].astype(str).str.strip().str.upper().map(fips_to_iso3)
    m = m.dropna(subset=["iso3"])
    usaid_unique = m.groupby("iso3")["col_57"].nunique().reset_index().rename(
        columns={"iso3": "ISO3", "col_57": "usaid_articles_unique"})
    df = df.merge(usaid_unique, on="ISO3", how="left")
    df["usaid_articles_unique"] = df["usaid_articles_unique"].fillna(0)

    denom = pd.read_csv(TOTAL_UNIQUE_URL)
    df = df.merge(denom, on="ISO3", how="left")
    df["attention_share_unique"] = df["usaid_articles_unique"] / df["total_articles_unique_url"]
    df["log_attention_share_unique"] = np.log1p(df["attention_share_unique"])

    g = pd.read_csv(GROSS_FILE).rename(columns={"iso3": "ISO3"}).drop(columns=["country"])
    df = df.merge(g, on="ISO3", how="left")
    wdi = pd.read_csv(WDI_SNAPSHOT)[["ISO3", "population_avg", "gdp_avg"]]
    if gdp is not None:
        wdi = wdi.drop(columns=["gdp_avg"]).merge(gdp[["ISO3", "gdp_avg"]], on="ISO3", how="left")
    df = df.merge(wdi, on="ISO3", how="left")
    for col, logcol in [("us_gross_mean", "log_us_gross"), ("dac_gross_mean", "log_dac_gross"),
                        ("us_share", "log_us_share"), ("population_avg", "log_pop"), ("gdp_avg", "log_gdp")]:
        df[logcol] = np.log(df[col].where(df[col] > 0))
    # aid over gdp, as in share_main load() and followup b3 (fractions)
    df["us_gdp"] = df["us_gross_mean"] * 1_000_000 / df["gdp_avg"]
    df["dac_gdp"] = df["dac_gross_mean"] * 1_000_000 / df["gdp_avg"]
    return df


def ols_hc3(y, xs, data):
    reg = data[[y] + xs].dropna()
    return smf.ols(f"{y} ~ {' + '.join(xs)}", data=reg).fit(cov_type="HC3")


def table1_row(df, col):
    # as share_main table1(): percent, s with ddof = 1
    d = df[["ISO3", col]].dropna()
    x = d[col] * 100
    return {"N": len(x), "mean": x.mean(), "s": x.std(ddof=1), "min": x.min(), "max": x.max(),
            "min_country": ", ".join(d.loc[x == x.min(), "ISO3"]), "max_country": ", ".join(d.loc[x == x.max(), "ISO3"])}


def b3_sample(df):
    # followup b3: countries with gdp > 0, and the two aid / gdp logs
    d3 = df[df["gdp_avg"] > 0].copy()
    for new in ["us_gdp", "dac_gdp"]:
        d3[f"log_{new}"] = np.log(d3[new].where(d3[new] > 0))
    return d3


def gdp_models(df):
    # every model that uses gdp: g7 (run_gross_aid.py) and b3 g8 / g9 (followup). one row per coefficient
    rows = []

    def put(model, variant, y, scale, res, terms):
        for t in terms:
            rows.append({"model": model, "variant": variant, "outcome": y, "term": t, "N": int(res.nobs),
                         "beta_hat": res.params[t] * scale, "se_type": "HC3", "se": res.bse[t] * scale,
                         "p": res.pvalues[t], "r2": res.rsquared})

    for aid, label in [("log_disbursements", "net"), ("log_us_gross", "gross")]:
        for y, scale in OUTCOMES:
            res = ols_hc3(y, [aid, "log_pop", "log_gdp"], df)
            put(f"G7 {'days' if y == DAYS else 'attention'}", label, y, scale, res, [aid, "log_pop", "log_gdp"])
    d3 = b3_sample(df)
    for y, scale in OUTCOMES:
        put("G8", "B3 levels on the gdp sample", y, scale, ols_hc3(y, ["log_us_gross", "log_dac_gross"], d3),
            ["log_us_gross", "log_dac_gross"])
        put("G8", "B3 aid / gdp", y, scale, ols_hc3(y, ["log_us_gdp", "log_dac_gdp"], d3),
            ["log_us_gdp", "log_dac_gdp"])
        put("G9 log us_share", "B3 aid / gdp", y, scale, ols_hc3(y, ["log_us_share"], d3), ["log_us_share"])
        put("G9 ratio", "B3 aid / gdp", y, scale, ols_hc3(y, ["log_us_gdp"], d3), ["log_us_gdp"])
    return pd.DataFrame(rows)
