# share main: us share of gross dac aid as the central regressor, untransformed attention share as the
#   main outcome, ln(1 + share) as robustness (SPEC.md in this folder)
# reads: data/input/ (aid data, country codes, wdi snapshot), data/intermediate/ (matched rows,
#   unique url totals, aid_gross_2018_2022.csv), the three SPEC.md files (hash check only)
# writes: results.csv, equivalence.csv, table1_check.csv, draft_check.csv, log.txt and
#   table2_raw.csv (all overwritten)
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

sys.dont_write_bytecode = True

# paths copied from config.py (not imported: importing it makes folders under outputs/)
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ODA_DATA = ROOT / "data" / "input" / "3-29-v2_oda_data.csv"
COUNTRY_CODES = ROOT / "data" / "input" / "country-codes.csv"
WDI_SNAPSHOT = ROOT / "data" / "input" / "wdi_population_gdp.csv"
MATCHES_ROWS = ROOT / "data" / "intermediate" / "usaid_closure_v1" / "matches_rows.csv"
TOTAL_UNIQUE_URL = ROOT / "data" / "intermediate" / "total_articles_unique_url.csv"
GROSS_FILE = ROOT / "data" / "intermediate" / "aid_gross_2018_2022.csv"
SPEC_SHA = {OUT.parent / "SPEC.md": "1206e9d8c25e6f2d848bb47e44622df6a40f3eb03ef6e24f01753a9319501617",
            OUT.parent / "followup" / "SPEC.md": "a505781224401e01c3eb7ace536c08a8bf5804d8258e5f1c772f3b08e74b6a03",
            OUT / "SPEC.md": "118cfa564367e75dc5d314626b03b548708791a8c5a1f6092a11c35beac4eea0"}
SEED = 0
FEW = ["IRN", "ERI"]
TOL = 1e-8

# outcome column: (outcome name, transform, scale)
RAW, LOGA, DAYS = "attention_share_unique", "log_attention_share_unique", "log_days"
OUTCOMES = {RAW: ("attention share, unique urls (main)", "raw fraction", 1000),
            LOGA: ("attention share, unique urls (robustness)", "ln(1 + share)", 1000),
            DAYS: ("days to first article", "ln(1 + days)", 1)}
ATT = [RAW, LOGA]
TERMS = {"S": "ln(us_share)", "T": "ln(dac_gross_mean)", "U": "ln(us_gross_mean)"}
MODELS = {"M1": ["S"], "M2": ["S", "T"], "M3": ["U", "T"], "M4": ["U"]}
# outcomes per full-sample model: days only for M1 (the draft's timing number)
FULL = {"M1": ATT + [DAYS], "M2": ATT, "M3": ATT, "M4": ATT}
SAMPLES = ["full", "(a) matched urls >= 5", "(b) matched urls >= 10", "(c) drop IRN ERI"]
NOTE_SCALE = {1000: "beta_hat and se times 1,000.", 1: "not scaled."}
NOTE_AID = ("gross oda, oecd dac2a measure 240, constant 2024 usd millions, 2018-2022 mean, missing year = 0. "
            "outcome: international news attention associated with a country's event geography.")

# pre-check, values of gross_aid/results.csv: (label, outcome, regressors, term, expected, decimals, n)
CHECK = [("G9 days", DAYS, ["S"], "S", -0.0958, 4, 95),
         ("G9 attention", LOGA, ["S"], "S", 0.4473, 4, 102),
         ("G8 days US", DAYS, ["U", "T"], "U", 0.0054, 4, None),
         ("G8 days DAC", DAYS, ["U", "T"], "T", -0.2968, 4, None),
         ("G8 attention US", LOGA, ["U", "T"], "U", 0.4321, 4, None),
         ("G8 attention DAC", LOGA, ["U", "T"], "T", -0.3871, 4, None)]

# draft table 1: (variable, column, scale, sample note, draft N, mean, sd, min, max) as strings
TABLE1 = [("attention share, unique urls, percent", "attention_share_unique", 100,
           "102", "0.107", "0.112", "0.000", "0.510"),
          ("matched usaid unique urls", "usaid_articles_unique", 1, "102", "18.40", "26.30", "0.00", "124.00"),
          ("total gdelt unique urls, thousands", "total_articles_unique_url", 1 / 1000,
           "102", "29.276", "71.390", "0.681", "626.076"),
          ("gross us oda, usd millions", "us_gross_mean", 1, "102", "248.98", "356.67", "0.22", "2187.07"),
          ("gross dac oda, usd millions", "dac_gross_mean", 1, "102", "781.28", "886.77", "17.33", "4563.85"),
          ("us share of gross dac oda, percent", "us_share", 100, "102", "29.16", "19.58", "0.83", "91.75"),
          ("gross us oda / gdp, percent", "us_gdp", 100, "100", "1.16", "3.00", "0.00", "26.89"),
          ("gross dac oda / gdp, percent", "dac_gdp", 100, "100", "2.92", "4.52", "0.03", "30.54"),
          ("days to first recorded coverage", "days_to_first_article", 1, "95", "23.10", "40.60", "1.00", "253.00")]

ROWS, EQ, T1, DRAFT = [], [], [], []
FITS = {}


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
    return Path(p).relative_to(ROOT).as_posix()


def header(text):
    print("\n" + "-" * 72 + f"\n{text}\n" + "-" * 72)


def load():
    # lines copied from gross_aid/run_gross_aid.py load()
    df = pd.read_csv(ODA_DATA)
    print(f"loaded 3-29-v2_oda_data.csv: N = {len(df)}")
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
    wdi = pd.read_csv(WDI_SNAPSHOT)[["ISO3", "gdp_avg"]]
    df = df.merge(wdi, on="ISO3", how="left")
    # new: short names for the regressors (same <= 0 rule)
    for col, name in [("us_share", "S"), ("dac_gross_mean", "T"), ("us_gross_mean", "U"),
                      ("total_articles_unique_url", "V")]:
        df[name] = np.log(df[col].where(df[col] > 0))
    # aid over gdp, as in gross_aid/followup b3 (fractions; table 1 shows percent)
    df["us_gdp"] = df["us_gross_mean"] * 1_000_000 / df["gdp_avg"]
    df["dac_gdp"] = df["dac_gross_mean"] * 1_000_000 / df["gdp_avg"]
    print(f"analysis file: N = {len(df)}")
    for c in ["attention_share_unique", "days_to_first_article", "S", "T", "U", "V", "gdp_avg"]:
        print(f"  N non-missing {c}: {df[c].notna().sum()}")
    return df


def ols_hc3(y, xs, data):
    reg = data[[y] + xs].dropna()
    return smf.ols(f"{y} ~ {' + '.join(xs)}", data=reg).fit(cov_type="HC3")


def add(model, y, sample, n, term, b, se_type, se, p, r2=np.nan, outcome=None, transform=None, note=""):
    name, tr, scale = OUTCOMES.get(y, (outcome, transform, 1))
    ROWS.append({"model": model, "outcome": name, "outcome_transform": tr, "sample": sample, "N": n,
                 "term": TERMS[term], "beta_hat": b * scale, "se_type": se_type, "se": se * scale, "p": p,
                 "r2": r2, "note": f"{NOTE_SCALE[scale]} {NOTE_AID} {note}".strip()})
    print(f"  {model:<4} | {tr:<13} | {sample:<26} | N = {n:>3} | {TERMS[term]:<29} | "
          f"beta_hat = {b * scale:+.4f} | {se_type} SE = {se * scale:.4f} | p = {p:.4f}"
          + ("" if np.isnan(r2) else f" | R2 = {r2:.4f}"))


def run_ols(model, y, sample, data, note=""):
    xs = MODELS[model]
    res = ols_hc3(y, xs, data)
    FITS[(model, y, sample)] = res
    for x in xs:
        add(model, y, sample, int(res.nobs), x, res.params[x], "HC3", res.bse[x], res.pvalues[x],
            res.rsquared, note=note)
    return res


def run_nb(model, xs, sample, data):
    # same as G6 in gross_aid/run_gross_aid.py, with a list of regressors
    nb = data.dropna(subset=["usaid_articles_unique", "total_articles_unique_url"] + xs)
    nb = nb[nb["total_articles_unique_url"] > 0].copy()
    nb["log_exposure"] = np.log(nb["total_articles_unique_url"])
    fit = smf.glm(f"usaid_articles_unique ~ {' + '.join(xs)}", data=nb, family=sm.families.NegativeBinomial(),
                  offset=nb["log_exposure"]).fit()
    for x in xs:
        add(model, None, sample, int(fit.nobs), x, fit.params[x], "model-based (MLE)", fit.bse[x],
            fit.pvalues[x], outcome="unique matched urls (count)", transform="count, log link",
            note="negative binomial glm, alpha 1, offset ln(total_articles_unique_url).")


def pre_check(df):
    header("PRE-CHECK: LOG VERSIONS OF G8 AND G9, TABLE 3 AND THE UNIQUE-URL TABLE 4 (net aid)")
    fails = []
    for label, y, xs, term, exp, dec, n in CHECK:
        res = ols_hc3(y, xs, df)
        got = round(res.params[term] * OUTCOMES[y][2], dec)
        ok = got == exp and (n is None or int(res.nobs) == n)
        print(f"  {label}: expected {exp}" + ("" if n is None else f" (N {n})") +
              f", got {got} (N {int(res.nobs)}): {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(label)
    r3 = ols_hc3(DAYS, ["log_disbursements"], df)
    got3 = (round(float(r3.params["log_disbursements"]), 4), int(r3.nobs), round(float(r3.bse["log_disbursements"]), 4))
    ok = got3 == (-0.1695, 93, 0.0551)
    print(f"  table 3 (net): expected (-0.1695, N 93, HC3 SE 0.0551), got {got3}: {'ok' if ok else 'FAIL'}")
    if not ok:
        fails.append("table 3")
    r4 = ols_hc3(LOGA, ["log_disbursements"], df)
    got4 = (round(float(r4.params["log_disbursements"]) * 1000, 3), int(r4.nobs))
    ok = got4 == (0.224, 100)
    print(f"  unique-url attention (net, log outcome, per 1,000): expected (0.224, N 100), got {got4}: "
          f"{'ok' if ok else 'FAIL'}")
    if not ok:
        fails.append("unique-url attention")
    if fails:
        print("\nPRE-CHECK FAILED, stopping. no new model was run.")
        for f in fails:
            print(f"  - {f}")
        sys.exit(1)
    print("pre-check: all match")


def eq_row(check, y, a_name, a, b_name, b, n):
    diff = float(np.max(np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float))))
    a1 = float(np.asarray(a).ravel()[0]) if np.size(a) == 1 else np.nan
    b1 = float(np.asarray(b).ravel()[0]) if np.size(b) == 1 else np.nan
    EQ.append({"check": check, "outcome": OUTCOMES[y][1] if y else "", "N": n, "quantity_a": a_name, "value_a": a1,
               "quantity_b": b_name, "value_b": b1, "max_abs_diff": diff, "tolerance": TOL if y else np.nan,
               "result": ("pass" if diff < TOL else "fail") if y else "", "note": "unscaled coefficients and se."})
    vals = f"{a_name} = {a1:.10g} | {b_name} = {b1:.10g}" if np.size(a) == 1 else f"{a_name} vs {b_name}"
    print(f"  {check:<30} | {OUTCOMES[y][1] if y else '':<13} | {vals} | max abs diff = {diff:.3e}" + (f" | {'pass' if diff < TOL else 'fail'}" if y else ""))


def equivalence(df):
    header("EQUIVALENCE OF M2 (S + T) AND M3 (U + T), FULL SAMPLE")
    for y in ATT:
        m2, m3 = FITS[("M2", y, "full")], FITS[("M3", y, "full")]
        n = int(m2.nobs)
        if not m2.fittedvalues.index.equals(m3.fittedvalues.index):
            print(f"  {y}: M2 and M3 samples differ")
        eq_row("1a fitted values", y, "M2 fitted (all)", m2.fittedvalues.values, "M3 fitted (all)",
               m3.fittedvalues.values, n)
        eq_row("1b r2", y, "M2 r2", m2.rsquared, "M3 r2", m3.rsquared, n)
        eq_row("2 coef S (M2) = coef U (M3)", y, "M2 b_S", m2.params["S"], "M3 b_U", m3.params["U"], n)
        eq_row("3 coef T (M2) = b_U + b_T (M3)", y, "M2 b_T", m2.params["T"], "M3 b_U + b_T",
               m3.params["U"] + m3.params["T"], n)
        v = m3.cov_params()
        eq_row("4 hc3 se T (M2)", y, "M2 se_T", m2.bse["T"], "sqrt(v_U + v_T + 2 cov_UT) M3",
               np.sqrt(v.loc["U", "U"] + v.loc["T", "T"] + 2 * v.loc["U", "T"]), n)

    header("COLLINEARITY (full sample, pairwise complete)")
    for a, b in [("S", "T"), ("U", "T")]:
        d = df[[a, b]].dropna()
        r = d[a].corr(d[b])
        vif = 1 / (1 - r ** 2)
        EQ.append({"check": f"collinearity corr({a}, {b})", "outcome": "", "N": len(d),
                   "quantity_a": f"pearson r {TERMS[a]}, {TERMS[b]}", "value_a": r,
                   "quantity_b": "vif = 1 / (1 - r^2)", "value_b": vif, "max_abs_diff": np.nan,
                   "tolerance": np.nan, "result": "", "note": "full sample, pairwise complete."})
        print(f"  corr({a}, {b}) = {r:.4f}, vif = {vif:.4f} (N = {len(d)})")


def fmt(x, dec):
    return f"{x:.{dec}f}"


def decs(s):
    return len(s.split(".")[1]) if "." in s else 0


def table1(df):
    header("TABLE 1 RECOMPUTATION (102 sample countries)")
    miss = df[df["gdp_avg"].isna()]
    print(f"countries with missing gdp_avg: N = {len(miss)}: "
          + ", ".join(f"{i} ({c})" for i, c in zip(miss["ISO3"], miss["country"])))
    for var, col, scale, dn, dmean, dsd, dmin, dmax in TABLE1:
        d = df[["ISO3", col]].dropna()
        x = d[col] * scale
        n, mean, sd1, sd0, lo, hi = len(x), x.mean(), x.std(ddof=1), x.std(ddof=0), x.min(), x.max()
        lo_c = ", ".join(d.loc[x == lo, "ISO3"])
        hi_c = ", ".join(d.loc[x == hi, "ISO3"])
        m = {"N": str(n) == dn, "mean": fmt(mean, decs(dmean)) == dmean, "sd": fmt(sd1, decs(dsd)) == dsd,
             "min": fmt(lo, decs(dmin)) == dmin, "max": fmt(hi, decs(dmax)) == dmax}
        sd0_m = fmt(sd0, decs(dsd)) == dsd
        T1.append({"variable": var, "N": n, "mean": mean, "sd": sd1, "sd_ddof0": sd0, "min": lo, "max": hi,
                   "min_country": lo_c, "max_country": hi_c, "draft_N": dn, "draft_mean": dmean, "draft_sd": dsd,
                   "draft_min": dmin, "draft_max": dmax, **{f"match_{k}": v for k, v in m.items()},
                   "match_sd_ddof0": sd0_m, "all_match": all(m.values())})
        print(f"\n  {var}")
        print(f"    N = {n} (draft {dn}) {'ok' if m['N'] else 'DIFF'}")
        print(f"    mean = {mean:.6f} (draft {dmean}) {'ok' if m['mean'] else 'DIFF'}")
        print(f"    sd ddof=1 = {sd1:.6f}, ddof=0 = {sd0:.6f} (draft {dsd}) ddof=1 {'ok' if m['sd'] else 'DIFF'}, "
              f"ddof=0 {'ok' if sd0_m else 'DIFF'}")
        print(f"    min = {lo:.6f} [{lo_c}] (draft {dmin}) {'ok' if m['min'] else 'DIFF'}")
        print(f"    max = {hi:.6f} [{hi_c}] (draft {dmax}) {'ok' if m['max'] else 'DIFF'}")

    header("TABLE 1: SENTENCE CHECKS")
    sh = df["us_share"] * 100
    below = df.loc[sh < 1, "ISO3"].tolist()
    print(f"  us share 'from less than 1% to nearly 92%': min = {sh.min():.4f}%, max = {sh.max():.4f}%; "
          f"countries below 1%: N = {len(below)} ({', '.join(below)})")
    sentence("us share range: min below 1%", "< 1%", f"{sh.min():.4f}%", sh.min() < 1)
    sentence("us share range: max 'nearly 92%'", "nearly 92%", f"{sh.max():.4f}%", 91.5 <= sh.max() < 92)
    sentence("countries with us share below 1%", "(not stated)", str(len(below)), None)
    us = df["us_gross_mean"]
    sentence("us aid min '$0.22 million'", "0.22", fmt(us.min(), 2), fmt(us.min(), 2) == "0.22")
    sentence("us aid max 'over $2.18 billion'", "> 2180 (usd millions)", fmt(us.max(), 2), us.max() > 2180)
    att = df["attention_share_unique"] * 100
    sentence("mean attention 0.107%", "0.107", fmt(att.mean(), 3), fmt(att.mean(), 3) == "0.107")
    sentence("sd attention 0.112 percentage points", "0.112", fmt(att.std(ddof=1), 3),
             fmt(att.std(ddof=1), 3) == "0.112")
    days = df["days_to_first_article"].dropna()
    sentence("timing 'from 1 to 253 days' (min)", "1", fmt(days.min(), 0), fmt(days.min(), 0) == "1")
    sentence("timing 'from 1 to 253 days' (max)", "253", fmt(days.max(), 0), fmt(days.max(), 0) == "253")
    sentence("'average delay 23.1 days'", "23.1", fmt(days.mean(), 1), fmt(days.mean(), 1) == "23.1")
    sentence("countries with a first-article date", "95", str(len(days)), len(days) == 95)
    zero = df.loc[df["usaid_articles_unique"] == 0, "ISO3"].tolist()
    sentence("countries without matched coverage (usaid_articles_unique = 0)", "7", str(len(zero)), len(zero) == 7)
    print(f"    countries with usaid_articles_unique = 0: {', '.join(zero)}")
    nodate = df.loc[df["days_to_first_article"].isna(), "ISO3"].tolist()
    print(f"    countries without a first-article date: {', '.join(nodate)}")


def sentence(item, draft, ours, ok):
    flag = "" if ok is None else ("match" if ok else "mismatch")
    DRAFT.append({"item": f"table 1 text: {item}", "draft_value": draft, "our_value": ours, "match": flag})
    print(f"  {item}: draft {draft}, ours {ours}" + (f": {flag}" if flag else ""))


def find(model, y, sample, term):
    r = [row for row in ROWS if row["model"] == model and row["outcome_transform"] == OUTCOMES[y][1]
         and row["sample"] == sample and row["term"] == TERMS[term]]
    return r[0]


def draft_table2():
    header("DRAFT TABLE 2 AND RESULTS TEXT")
    items = [("col 1 ln gross us oda (M4, log outcome)", "M4", LOGA, "full", "U", "0.212", "0.057", None,
              "0.115", "102"),
             ("col 2 ln us share (M1, log outcome)", "M1", LOGA, "full", "S", "0.447", "0.099", None, "0.165", None),
             ("col 3 ln us share (M2, log outcome)", "M2", LOGA, "full", "S", "0.432", "0.110", None, "0.167", None),
             ("col 3 ln gross dac oda (M2, log outcome)", "M2", LOGA, "full", "T", "0.045", "0.098", "0.645",
              None, None),
             ("untransformed: ln us share, baseline (M1, raw)", "M1", RAW, "full", "S", "0.448", None, None, None,
              None),
             ("untransformed: ln us share, with total dac (M2, raw)", "M2", RAW, "full", "S", "0.433", None, None,
              None, None)]
    for y in [RAW, LOGA]:
        items += [(f"restriction >= 5: ln us share (M1, {OUTCOMES[y][1]})", "M1", y, "(a) matched urls >= 5", "S",
                   "0.611", None, "< 0.001", None, None),
                  (f"restriction >= 10: ln us share (M1, {OUTCOMES[y][1]})", "M1", y, "(b) matched urls >= 10", "S",
                   "0.647", None, "0.002", None, None)]
    items.append(("timing: ln us share (M1, days)", "M1", DAYS, "full", "S", "-0.096", None, "0.330", None, "95"))
    for item, model, y, sample, term, b, se, p, r2, n in items:
        r = find(model, y, sample, term)
        for what, dv, ov in [("beta", b, r["beta_hat"]), ("se", se, r["se"]), ("p", p, r["p"]),
                             ("r2", r2, r["r2"]), ("N", n, r["N"])]:
            if dv is None:
                continue
            if dv.startswith("<"):
                ours, ok = f"{ov:.6f}", ov < float(dv[1:])
            elif what == "N":
                ours, ok = str(ov), str(ov) == dv
            else:
                ours = fmt(ov, decs(dv))
                ok = ours == dv
            DRAFT.append({"item": f"table 2 / text: {item}: {what}", "draft_value": dv, "our_value": ours,
                          "match": "match" if ok else "mismatch"})
            print(f"  {item}: {what}: draft {dv}, ours {ours} (N {r['N']}): {'match' if ok else 'MISMATCH'}")
    print("  note: the draft does not say which attention outcome the >= 5 and >= 10 rows use; both are compared.")


def raw_vs_log(df):
    header("RAW SHARE VS ln(1 + SHARE)")
    d = df[[RAW, LOGA]].dropna()
    diff = (d[RAW] - d[LOGA]).abs()
    print(f"  N = {len(d)}; largest abs difference = {diff.max():.6e} "
          f"(at {df.loc[diff.idxmax(), 'ISO3']}, share = {d.loc[diff.idxmax(), RAW]:.6f}); "
          f"pearson r = {d[RAW].corr(d[LOGA]):.10f}")


def compare_signs():
    header("RAW VS LOG OUTCOME: SIGN AND SIGNIFICANCE (same model, sample and term)")
    for row in ROWS:
        if row["outcome_transform"] != "raw fraction":
            continue
        lg = [r for r in ROWS if r["model"] == row["model"] and r["outcome_transform"] == "ln(1 + share)"
              and r["sample"] == row["sample"] and r["term"] == row["term"]][0]
        sign = "same sign" if np.sign(row["beta_hat"]) == np.sign(lg["beta_hat"]) else "SIGN CHANGE"
        sig = []
        for a in [0.05, 0.10]:
            if (row["p"] < a) != (lg["p"] < a):
                sig.append(f"crosses p {a:.2f} (log p = {lg['p']:.4f}, raw p = {row['p']:.4f})")
        print(f"  {row['model']} | {row['sample']:<26} | {row['term']:<20} | log {lg['beta_hat']:+.4f} "
              f"(p {lg['p']:.4f}) | raw {row['beta_hat']:+.4f} (p {row['p']:.4f}) | {sign}"
              + (" | " + "; ".join(sig) if sig else ""))


def table2_raw():
    # draft table 2 layout from rows already in ROWS (no new model): raw outcome, then ln(1 + share)
    header("TABLE 2, RAW OUTCOME (ln(1 + share) in extra columns), per 1,000, HC3")
    out = []
    specs = [("(1) ln(US aid)", "M4", "U", ["full"]),
             ("(2) ln(US share)", "M1", "S", SAMPLES),
             ("(3) ln(US share) + ln(total gross DAC aid)", "M2", "S", SAMPLES)]
    for label, model, main, samples in specs:
        for sample in samples:
            row = {"model": label, "sample": sample, "main_term": TERMS[main]}
            for pre, y in [("raw", RAW), ("log", LOGA)]:
                r = find(model, y, sample, main)
                row.update({f"{pre}_N": r["N"], f"{pre}_r2": r["r2"], f"{pre}_beta": r["beta_hat"],
                            f"{pre}_se": r["se"], f"{pre}_p": r["p"]})
                t = find(model, y, sample, "T") if model == "M2" else None
                row.update({f"{pre}_beta_total_dac": t["beta_hat"] if t else np.nan,
                            f"{pre}_se_total_dac": t["se"] if t else np.nan,
                            f"{pre}_p_total_dac": t["p"] if t else np.nan})
            note = ("raw = attention share (fraction); log = ln(1 + share). beta and se times 1,000, hc3 se. "
                    "p-values for the total-aid coefficient are included for all samples.")
            if model == "M4":
                note += " model (1) is given for the full sample only."
            row["note"] = note
            out.append(row)
            print(f"  {label:<44} | {sample:<22} | N = {row['raw_N']:>3} | raw {row['raw_beta']:+.3f} "
                  f"({row['raw_se']:.3f}) p {row['raw_p']:.4f} | log {row['log_beta']:+.3f} ({row['log_se']:.3f}) "
                  f"p {row['log_p']:.4f}" + ("" if model != "M2" else
                  f" | total dac raw {row['raw_beta_total_dac']:+.3f} ({row['raw_se_total_dac']:.3f}) "
                  f"p {row['raw_p_total_dac']:.4f}, log p {row['log_p_total_dac']:.4f}"))
    return pd.DataFrame(out)


def main():
    np.random.seed(SEED)  # nothing below is random
    sys.stdout = Tee(OUT / "log.txt")
    print("=" * 72 + "\nshare main (gross_aid/share_main/run_share_main.py)\n" + "=" * 72)
    for path, sha in SPEC_SHA.items():
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"{rel(path)} sha-256: {got}: {'ok' if got == sha else 'FAIL'}")
        if got != sha:
            print("SPEC CHECK FAILED, stopping.")
            sys.exit(1)
    df = load()
    pre_check(df)

    header("M1 TO M4, FULL SAMPLE (ols, hc3)")
    for model, ys in FULL.items():
        for y in ys:
            run_ols(model, y, "full", df)
    print("\n  M4 vs the old G2 (log attention, 0.21245, N 102):")
    for y, old in [(LOGA, 0.21245)]:
        r = find("M4", y, "full", "U")
        print(f"    {OUTCOMES[y][1]}: M4 = {r['beta_hat']:.5f} (N {r['N']}), old = {old}: "
              f"{'same' if round(r['beta_hat'], 5) == old else 'DIFF'}")

    equivalence(df)
    raw_vs_log(df)

    header("ROBUSTNESS SAMPLES FOR M1 AND M2")
    note_ab = ("restriction on usaid_articles_unique, the numerator of the attention share, so it selects on "
               "the outcome.")
    samples = [("(a) matched urls >= 5", df[df["usaid_articles_unique"] >= 5], note_ab),
               ("(b) matched urls >= 10", df[df["usaid_articles_unique"] >= 10], note_ab),
               ("(c) drop IRN ERI", df[~df["ISO3"].isin(FEW)], "IRN and ERI dropped (2 and 3 years of us data).")]
    for name, d, _ in samples:
        drop = df[~df.index.isin(d.index)].sort_values(["usaid_articles_unique", "ISO3"])
        print(f"  {name}: kept N = {len(d)}, dropped N = {len(drop)}: "
              + ", ".join(f"{i} ({int(c)})" for i, c in zip(drop["ISO3"], drop["usaid_articles_unique"])))
    for name, d, note in samples:
        print(f"\n  {name}")
        for model in ["M1", "M2"]:
            for y in ATT:
                run_ols(model, y, name, d, note)

    header("NEGATIVE BINOMIAL (model-based se)")
    run_nb("NB S", ["S"], "full", df)
    run_nb("NB S + T", ["S", "T"], "full", df)

    compare_signs()
    table1(df)
    draft_table2()
    t2 = table2_raw()

    pd.DataFrame(ROWS).to_csv(OUT / "results.csv", index=False)
    pd.DataFrame(EQ).to_csv(OUT / "equivalence.csv", index=False)
    pd.DataFrame(T1).to_csv(OUT / "table1_check.csv", index=False)
    pd.DataFrame(DRAFT).to_csv(OUT / "draft_check.csv", index=False)
    t2.to_csv(OUT / "table2_raw.csv", index=False)
    print(f"\nwrote results.csv ({len(ROWS)} rows), equivalence.csv ({len(EQ)} rows), "
          f"table1_check.csv ({len(T1)} rows), draft_check.csv ({len(DRAFT)} rows), "
          f"table2_raw.csv ({len(t2)} rows)")


if __name__ == "__main__":
    main()
