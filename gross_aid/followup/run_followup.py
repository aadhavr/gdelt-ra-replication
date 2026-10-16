# gross aid follow-up: part a (irn and eri data checks), then b1 to b3 of SPEC.md in this folder
# reads: data/raw/oecd_gross_us_2018_2022.csv, oecd_gross_dac_2018_2022.csv, data/input/ (aid data,
#   country codes, wdi snapshot), data/intermediate/ (matched rows, unique url totals, aid_gross_2018_2022.csv),
#   gross_aid/results.csv (check only)
# writes: results.csv and log.txt in this folder (both overwritten)
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

# import config.py from the repo root, without writing bytecode into the repo
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

OUT = Path(__file__).resolve().parent
GROSS_DIR = OUT.parent
GROSS_FILE = config.INTERMEDIATE_DIR / "aid_gross_2018_2022.csv"
US_FILE = config.RAW_DIR / "oecd_gross_us_2018_2022.csv"
DAC_FILE = config.RAW_DIR / "oecd_gross_dac_2018_2022.csv"
SPEC_SHA = {GROSS_DIR / "SPEC.md": "1206e9d8c25e6f2d848bb47e44622df6a40f3eb03ef6e24f01753a9319501617",
            OUT / "SPEC.md": "a505781224401e01c3eb7ace536c08a8bf5804d8258e5f1c772f3b08e74b6a03"}
FEW = ["IRN", "ERI"]
THRESHOLDS = [5, 10]
SEED = 0

DAYS = "log(1 + days to first article)"
ATTN = "log(1 + unique-URL attention share), beta_hat and SE per 1,000"
OUTCOMES = [("log_days", DAYS, 1), ("log_attention_share_unique", ATTN, 1000)]

# full-sample gross values from gross_aid/results.csv: (model, outcome, coefficient, expected, decimals, n)
CHECK = [("G1", "log_days", "log_us_gross", -0.16708, 5, 95),
         ("G2", "log_attention_share_unique", "log_us_gross", 0.21245, 5, 102),
         ("G8", "log_days", "log_us_gross", 0.0054, 4, None),
         ("G8", "log_days", "log_dac_gross", -0.2968, 4, None),
         ("G8", "log_attention_share_unique", "log_us_gross", 0.4321, 4, None),
         ("G8", "log_attention_share_unique", "log_dac_gross", -0.3871, 4, None),
         ("G9", "log_days", "log_us_share", -0.0958, 4, None),
         ("G9", "log_attention_share_unique", "log_us_share", 0.4473, 4, None)]

ROWS = []


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


def rel(p):
    return Path(p).relative_to(config.ROOT).as_posix()


def header(text):
    print("\n" + "-" * 72 + f"\n{text}\n" + "-" * 72)


def load():
    # lines copied from gross_aid/run_gross_aid.py load()
    df = pd.read_csv(config.ODA_DATA)
    print(f"loaded 3-29-v2_oda_data.csv: N = {len(df)}")
    df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()
    df["us_oda_disbursements"] = df["us_oda_disbursements"].astype(str).str.replace(",", "")
    df["us_oda_disbursements"] = pd.to_numeric(df["us_oda_disbursements"], errors="coerce")
    df["days_to_first_article"] = pd.to_numeric(df["days_to_first_article"], errors="coerce")
    df["log_days"] = np.log1p(df["days_to_first_article"])

    cc_raw = pd.read_csv(config.COUNTRY_CODES, dtype=str)
    cc_raw["FIPS"] = cc_raw["FIPS"].astype(str).str.strip().str.upper()
    fips_to_iso3 = dict(zip(cc_raw["FIPS"], cc_raw["ISO3166-1-Alpha-3"]))
    m = pd.read_csv(config.MATCHES_ROWS, dtype=str, low_memory=False)
    m["iso3"] = m["col_51"].astype(str).str.strip().str.upper().map(fips_to_iso3)
    m = m.dropna(subset=["iso3"])
    usaid_unique = m.groupby("iso3")["col_57"].nunique().reset_index().rename(
        columns={"iso3": "ISO3", "col_57": "usaid_articles_unique"})
    df = df.merge(usaid_unique, on="ISO3", how="left")
    df["usaid_articles_unique"] = df["usaid_articles_unique"].fillna(0)

    denom = pd.read_csv(config.TOTAL_UNIQUE_URL)
    df = df.merge(denom, on="ISO3", how="left")
    df["attention_share_unique"] = df["usaid_articles_unique"] / df["total_articles_unique_url"]
    df["log_attention_share_unique"] = np.log1p(df["attention_share_unique"])

    g = pd.read_csv(GROSS_FILE).rename(columns={"iso3": "ISO3"}).drop(columns=["country"])
    df = df.merge(g, on="ISO3", how="left")
    wdi = pd.read_csv(config.WDI_SNAPSHOT)[["ISO3", "population_avg", "gdp_avg"]]
    df = df.merge(wdi, on="ISO3", how="left")
    add_logs(df)
    print(f"analysis file: N = {len(df)}")
    return df


def add_logs(df):
    # same rule as run_gross_aid.py: a value <= 0 gives a missing log
    for col, logcol in [("us_gross_mean", "log_us_gross"), ("dac_gross_mean", "log_dac_gross"),
                        ("us_share", "log_us_share")]:
        df[logcol] = np.log(df[col].where(df[col] > 0))


def ols_hc3(y, xs, data):
    reg = data[[y] + xs].dropna()
    return smf.ols(f"{y} ~ {' + '.join(xs)}", data=reg).fit(cov_type="HC3")


def add(model, variant, outcome, n, b, se, p, r2, note):
    ROWS.append({"model": model, "variant": variant, "outcome": outcome, "N": n, "beta_hat": b,
                 "se": se, "p": p, "r2": r2, "note": note})
    print(f"  {model:<22} | {variant:<34} | {'days' if outcome == DAYS else 'attention':<9} | N = {n:>3} | "
          f"beta_hat = {b:+.4f} | HC3 SE = {se:.4f} | p = {p:.4f} | R2 = {r2:.4f}")


def single(models, aid, variant, data, note):
    # models: one name per outcome (days, attention)
    for model, (y, outcome, scale) in zip(models, OUTCOMES):
        res = ols_hc3(y, [aid], data)
        add(model, variant, outcome, int(res.nobs), res.params[aid] * scale, res.bse[aid] * scale,
            res.pvalues[aid], res.rsquared, note)


def joint(names, us, dac, variant, data, note):
    # g8: both coefficients, pearson r, vif and the hc3 wald test, as in run_gross_aid.py
    for y, outcome, scale in OUTCOMES:
        res = ols_hc3(y, [us, dac], data)
        reg = data[[y, us, dac]].dropna()
        r = reg[us].corr(reg[dac])
        w = res.wald_test(f"{us} = 0, {dac} = 0", use_f=False, scalar=True)
        stats_ = (f"r = {r:.4f}; VIF = {1 / (1 - r ** 2):.4f}; HC3 wald both = 0: "
                  f"chi2(2) = {float(w.statistic):.4f}, p = {float(w.pvalue):.6g}")
        for var, name in zip([us, dac], names):
            add(name, variant, outcome, int(res.nobs), res.params[var] * scale, res.bse[var] * scale,
                res.pvalues[var], res.rsquared, f"{note} {stats_}".strip())
        print(f"    {stats_}")


def gross_set(variant, data, note=""):
    single(["G1 log us_gross", "G2 log us_gross"], "log_us_gross", variant, data, note)
    joint(["G8 log us_gross", "G8 log dac_gross"], "log_us_gross", "log_dac_gross", variant, data, note)
    single(["G9 log us_share"] * 2, "log_us_share", variant, data, note)


def part_a(df):
    header("PART A: IRN AND ERI IN THE OECD FILES (read only, no models)")
    us = pd.read_csv(US_FILE)
    dac = pd.read_csv(DAC_FILE)
    print(f"A1. {rel(US_FILE)}: rows N = {len(us)}, columns N = {len(us.columns)}")
    print("  columns: " + ", ".join(us.columns))
    for name, d in [("us file", us), ("dac file", dac)]:
        print(f"  {name} OBS_STATUS, whole file: {d['OBS_STATUS'].value_counts(dropna=False).to_dict()}; "
              f"'Observation status': {d['Observation status'].value_counts(dropna=False).to_dict()}")
        for iso in FEW:
            s = d[d["RECIPIENT"] == iso]
            print(f"  {name} OBS_STATUS, {iso}: {s['OBS_STATUS'].value_counts(dropna=False).to_dict()}")

    print("\nA2. years and values (USD millions, constant 2024 prices)")
    for iso in FEW:
        for name, d in [("us file", us), ("dac file", dac)]:
            s = d[d["RECIPIENT"] == iso].sort_values("TIME_PERIOD")
            vals = ", ".join(f"{t}: {v}" for t, v in zip(s["TIME_PERIOD"], s["OBS_VALUE"]))
            print(f"  {iso} {name}: years N = {len(s)}; {vals}")

    print("\nA3. us_gross_mean (sum / 5), sum / n_years, and net us_oda_disbursements")
    alt = {}
    for iso in FEW:
        s = us[us["RECIPIENT"] == iso]["OBS_VALUE"]
        tot, n = s.sum(), len(s)
        row = df[df["ISO3"] == iso].iloc[0]
        net = row["us_oda_disbursements"]
        by5, byn = tot / 5, tot / n
        closer = "sum / 5" if abs(by5 - net) < abs(byn - net) else "sum / n_years"
        print(f"  {iso}: sum = {tot:.6f}, n_years = {n}; sum / 5 = {by5:.6f} "
              f"(aid_gross_2018_2022.csv us_gross_mean = {row['us_gross_mean']:.6f}); "
              f"sum / n_years = {byn:.6f}; net = {net}")
        print(f"    |sum / 5 - net| = {abs(by5 - net):.6f}; |sum / n_years - net| = {abs(byn - net):.6f}; "
              f"closer to net: {closer}")
        alt[iso] = byn
    print("  the us file has no row for the other years. the data do not show whether those years are zero "
          "or not reported. the price base of the net sheet is not known.")
    return alt


def check_full(df):
    header("CHECK: FULL-SAMPLE GROSS VALUES OF gross_aid/results.csv")
    fails = []
    for model, y, var, exp, dec, n in CHECK:
        xs = {"G1": ["log_us_gross"], "G2": ["log_us_gross"], "G8": ["log_us_gross", "log_dac_gross"],
              "G9": ["log_us_share"]}[model]
        res = ols_hc3(y, xs, df)
        scale = 1000 if y == "log_attention_share_unique" else 1
        got = round(res.params[var] * scale, dec)
        ok = got == exp and (n is None or int(res.nobs) == n)
        print(f"  {model} {y} {var}: expected {exp}" + ("" if n is None else f" (N {n})") +
              f", got {got} (N {int(res.nobs)}): {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"{model} {y} {var}")
    if fails:
        print("\nCHECK FAILED, stopping. no new model was run.")
        for f in fails:
            print(f"  - {f}")
        sys.exit(1)
    print("check: all match")


def main():
    np.random.seed(SEED)  # nothing below is random
    sys.stdout = Tee(OUT / "log.txt")
    print("=" * 72 + "\ngross aid follow-up (gross_aid/followup/run_followup.py)\n" + "=" * 72)
    for path, sha in SPEC_SHA.items():
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"{rel(path)} sha-256: {got}: {'ok' if got == sha else 'FAIL'}")
        if got != sha:
            print("SPEC CHECK FAILED, stopping.")
            sys.exit(1)
    df = load()

    alt = part_a(df)
    check_full(df)

    header("B1: KEEP COUNTRIES WITH usaid_articles_unique >= 5 AND >= 10 (selects on the attention outcome)")
    note_b1 = ("restriction on usaid_articles_unique, the numerator of the attention share, so it selects "
               "on the outcome.")
    for thr in THRESHOLDS:
        drop = df[df["usaid_articles_unique"] < thr].sort_values(["usaid_articles_unique", "ISO3"])
        print(f"  threshold {thr}: kept N = {len(df) - len(drop)}, dropped N = {len(drop)} (of {len(df)}):")
        print("    " + ", ".join(f"{i} ({int(c)})" for i, c in zip(drop["ISO3"], drop["usaid_articles_unique"])))
    print()
    gross_set("full", df)
    for thr in THRESHOLDS:
        gross_set(f"B1 usaid_articles_unique >= {thr}", df[df["usaid_articles_unique"] >= thr], note_b1)

    header("B2: IRN AND ERI")
    print(df[df["ISO3"].isin(FEW)][["ISO3", "usaid_articles_unique", "days_to_first_article",
                                     "us_gross_mean", "n_years_us", "dac_gross_mean", "us_share"]].to_string(index=False))
    gross_set("B2 (i) drop IRN ERI", df[~df["ISO3"].isin(FEW)], "IRN and ERI dropped.")
    d2 = df.copy()
    for iso, v in alt.items():
        d2.loc[d2["ISO3"] == iso, "us_gross_mean"] = v
    d2["us_share"] = np.where(d2["dac_gross_mean"] > 0, d2["us_gross_mean"] / d2["dac_gross_mean"], np.nan)
    add_logs(d2)
    print("  variant (ii) values:")
    print(d2[d2["ISO3"].isin(FEW)][["ISO3", "us_gross_mean", "us_share"]].to_string(index=False))
    gross_set("B2 (ii) IRN ERI sum / n_years", d2,
              "IRN and ERI us_gross_mean = sum / n_years_us (2 and 3 years); us_share recomputed.")

    header("B3: AID OVER GDP (extra, not in the original spec)")
    print("  gdp_avg: WDI NY.GDP.MKTP.CD, current USD (not millions), 2018-2022 mean. aid: constant 2024 "
          "USD millions. ratio = aid x 1,000,000 / gdp_avg. the price bases differ (constant 2024 vs current).")
    miss = df[df["gdp_avg"].isna()]
    print(f"  gdp_avg missing N = {len(miss)}: {', '.join(miss['ISO3'])}")
    d3 = df[df["gdp_avg"] > 0].copy()
    print(f"  countries with gdp_avg > 0: N = {len(d3)}")
    for col, new in [("us_gross_mean", "us_gdp"), ("dac_gross_mean", "dac_gdp")]:
        d3[new] = d3[col] * 1_000_000 / d3["gdp_avg"]
        d3[f"log_{new}"] = np.log(d3[new].where(d3[new] > 0))
        print(f"  {new}: N > 0 = {d3[f'log_{new}'].notna().sum()}, median = {d3[new].median():.6f}")
    note_b3 = "extra, not in the original spec. countries with gdp_avg."
    joint(["G8 log us_gross", "G8 log dac_gross"], "log_us_gross", "log_dac_gross",
          "B3 levels on the gdp sample", d3, note_b3)
    joint(["G8 log us_gross/gdp", "G8 log dac_gross/gdp"], "log_us_gdp", "log_dac_gdp", "B3 aid / gdp", d3,
          note_b3 + " aid x 1,000,000 / gdp_avg; price bases differ.")
    single(["G9 log us_share"] * 2, "log_us_share", "B3 aid / gdp", d3,
           note_b3 + " us_gdp / dac_gdp = us_share, so the regressor is unchanged; sample change only.")
    single(["G9 ratio log us_gross/gdp"] * 2, "log_us_gdp", "B3 aid / gdp", d3,
           note_b3 + " aid x 1,000,000 / gdp_avg; price bases differ.")

    res = pd.DataFrame(ROWS)
    res.to_csv(OUT / "results.csv", index=False)
    print(f"\nwrote {rel(OUT / 'results.csv')}: {len(res)} rows")


if __name__ == "__main__":
    main()
