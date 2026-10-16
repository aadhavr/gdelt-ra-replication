# gross aid: baselines with net aid, then the models of SPEC.md with net and gross us aid
# reads: data/input/ (aid data, country codes, wdi snapshot), data/intermediate/ (matched rows,
#   unique url totals, aid_gross_2018_2022.csv from build_gross_aid.py)
# writes: results.csv and side_by_side.csv in this folder, adds its output to log.txt
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from lifelines import CoxPHFitter

# import config.py from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

OUT = Path(__file__).resolve().parent
GROSS_FILE = config.INTERMEDIATE_DIR / "aid_gross_2018_2022.csv"

NET_LABEL = "US aid (USD millions) (net)"
GROSS_LABEL = "US aid (USD millions) (gross)"
DAC_LABEL = "DAC aid (USD millions) (gross)"
SHARE_LABEL = "US share of DAC aid (gross)"
DAYS = "log(1 + days to first article)"
ATTN = "log(1 + unique-URL attention share), beta_hat and SE per 1,000"
NOTE = ("gross: OECD DAC2A measure 240, constant 2024 prices, USD millions, 2018-2022 mean, missing year = 0; "
        "IRN has 2 and ERI has 3 years of US data. net: us_oda_disbursements of 3-29-v2_oda_data.csv, "
        "price base not known. regressor = natural log of the aid variable; a value <= 0 leaves the model.")

# baselines from robustness/build_all.py: (beta_hat, n, hc3 se, p), rounded as stated
BASE_T3 = {"coef": -0.1695, "n": 93, "se": 0.0551, "p": 0.0021}
BASE_T4 = {"coef": 0.224, "n": 100, "p": 0.0002}

ROWS = []


class Tee:  # add everything printed to log.txt
    def __init__(self, path):
        self.file = open(path, "a")
        self.stdout = sys.stdout

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def load():
    # lines copied from robustness/build_all.py step 0 (region and raw-row parts left out)
    df = pd.read_csv(config.ODA_DATA)
    print(f"loaded 3-29-v2_oda_data.csv: N = {len(df)}")
    df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()
    df["us_oda_disbursements"] = df["us_oda_disbursements"].astype(str).str.replace(",", "")
    df["us_oda_disbursements"] = pd.to_numeric(df["us_oda_disbursements"], errors="coerce")
    df["days_to_first_article"] = pd.to_numeric(df["days_to_first_article"], errors="coerce")
    df["log_days"] = np.log1p(df["days_to_first_article"])
    df["log_disbursements"] = np.where(df["us_oda_disbursements"] > 0, np.log(df["us_oda_disbursements"]), np.nan)
    print(f"N with a first-article date: {df['days_to_first_article'].notna().sum()}")
    print(f"N with net aid > 0: {df['log_disbursements'].notna().sum()}")

    cc_raw = pd.read_csv(config.COUNTRY_CODES, dtype=str)
    cc_raw["FIPS"] = cc_raw["FIPS"].astype(str).str.strip().str.upper()
    fips_to_iso3 = dict(zip(cc_raw["FIPS"], cc_raw["ISO3166-1-Alpha-3"]))
    m = pd.read_csv(config.MATCHES_ROWS, dtype=str, low_memory=False)
    m["iso3"] = m["col_51"].astype(str).str.strip().str.upper().map(fips_to_iso3)
    m = m.dropna(subset=["iso3"])
    print(f"matched rows with a valid ISO3: N = {len(m)}")
    usaid_unique = m.groupby("iso3")["col_57"].nunique().reset_index().rename(
        columns={"iso3": "ISO3", "col_57": "usaid_articles_unique"})
    df = df.merge(usaid_unique, on="ISO3", how="left")
    df["usaid_articles_unique"] = df["usaid_articles_unique"].fillna(0)
    print(f"N with usaid_articles_unique > 0: {(df['usaid_articles_unique'] > 0).sum()}")

    denom = pd.read_csv(config.TOTAL_UNIQUE_URL)
    df = df.merge(denom, on="ISO3", how="left")
    print(f"N with total_articles_unique_url: {df['total_articles_unique_url'].notna().sum()}")
    df["log_total_articles_unique"] = np.log(df["total_articles_unique_url"].where(df["total_articles_unique_url"] > 0))
    df["attention_share_unique"] = df["usaid_articles_unique"] / df["total_articles_unique_url"]
    df["log_attention_share_unique"] = np.log1p(df["attention_share_unique"])
    print(f"N with an attention share: {df['attention_share_unique'].notna().sum()}")

    # new: gross aid and wdi
    g = pd.read_csv(GROSS_FILE).rename(columns={"iso3": "ISO3"}).drop(columns=["country"])
    df = df.merge(g, on="ISO3", how="left")
    print(f"N with a gross aid row: {df['us_gross_mean'].notna().sum()}")
    wdi = pd.read_csv(config.WDI_SNAPSHOT)[["ISO3", "population_avg", "gdp_avg"]]
    df = df.merge(wdi, on="ISO3", how="left")
    for col, logcol in [("us_gross_mean", "log_us_gross"), ("dac_gross_mean", "log_dac_gross"),
                        ("us_share", "log_us_share"), ("population_avg", "log_pop"), ("gdp_avg", "log_gdp")]:
        df[logcol] = np.log(df[col].where(df[col] > 0))
        print(f"N with {col} > 0: {df[logcol].notna().sum()}")
    df["net_sample"] = df["log_disbursements"].notna()
    return df


def ols_hc3(y, xs, data):
    reg = data[[y] + xs].dropna()
    return smf.ols(f"{y} ~ {' + '.join(xs)}", data=reg).fit(cov_type="HC3")


def add(model, label, sample, outcome, n, b, se_type, se, p, r2=np.nan):
    ROWS.append({"model": model, "aid_variable": label, "sample": sample, "outcome": outcome, "N": n,
                 "beta_hat": b, "se_type": se_type, "se": se, "p": p, "r2": r2, "note": NOTE})
    print(f"  {model} | {label} | {sample} | N = {n} | beta_hat = {b:.6f} | {se_type} SE = {se:.6f} | "
          f"p = {p:.6f}" + ("" if np.isnan(r2) else f" | R2 = {r2:.4f}"))


def run_ols(model, aid, label, sample, data, y, extra=()):
    xs = [aid] + list(extra)
    res = ols_hc3(y, xs, data)
    scale = 1000 if y == "log_attention_share_unique" else 1
    outcome = ATTN if scale == 1000 else DAYS
    add(model, label, sample, outcome, int(res.nobs), res.params[aid] * scale, "HC3",
        res.bse[aid] * scale, res.pvalues[aid], res.rsquared)
    return res


def run_cox(model, aid, label, sample, data, extra=()):
    # same as run_cox in build_all.py, with the aid column as a parameter
    cols = ["days_to_first_article", aid] + list(extra)
    surv = data[cols].dropna(subset=[c for c in cols if c != "days_to_first_article"]).copy()
    surv["event"] = surv["days_to_first_article"].notna().astype(int)
    surv["time"] = surv["days_to_first_article"].fillna(365.0).clip(upper=365.0)  # no article = censored at 365 days
    cph = CoxPHFitter()
    cph.fit(surv[["time", "event", aid] + list(extra)], duration_col="time", event_col="event")
    print(f"  cox sample N = {len(surv)}, events = {int(surv['event'].sum())}, censored = {int((surv['event'] == 0).sum())}")
    add(model, label, sample, "hazard of first article (log-hazard; positive = faster)", len(surv),
        cph.params_[aid], "Cox model-based", cph.standard_errors_[aid], cph.summary.loc[aid, "p"])


def run_nb(model, aid, label, sample, data):
    # same as table b3 in build_all.py, with the aid column as a parameter
    nb = data.dropna(subset=["usaid_articles_unique", "total_articles_unique_url", aid])
    nb = nb[nb["total_articles_unique_url"] > 0].copy()
    nb["log_exposure"] = np.log(nb["total_articles_unique_url"])
    fit = smf.glm(f"usaid_articles_unique ~ {aid}", data=nb, family=sm.families.NegativeBinomial(),
                  offset=nb["log_exposure"]).fit()
    add(model, label, sample, "unique matched URLs (count), offset log(total unique URLs)", int(fit.nobs),
        fit.params[aid], "model-based (MLE)", fit.bse[aid], fit.pvalues[aid])


def baselines(df):
    print("\n" + "-" * 72 + "\nPART 2: BASELINES WITH NET AID\n" + "-" * 72)
    fails = []
    r3 = ols_hc3("log_days", ["log_disbursements"], df)
    got3 = {"coef": round(r3.params["log_disbursements"], 4), "n": int(r3.nobs),
            "se": round(r3.bse["log_disbursements"], 4), "p": round(r3.pvalues["log_disbursements"], 4)}
    print(f"table 3: N = {int(r3.nobs)}  beta_hat = {r3.params['log_disbursements']:.6f}  "
          f"HC3 SE = {r3.bse['log_disbursements']:.6f}  p = {r3.pvalues['log_disbursements']:.6f}")
    for k, v in BASE_T3.items():
        ok = got3[k] == v
        print(f"  {k}: expected {v}, got {got3[k]}: {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"table 3 {k}: expected {v}, got {got3[k]}")
    r4 = ols_hc3("log_attention_share_unique", ["log_disbursements"], df)
    got4 = {"coef": round(r4.params["log_disbursements"] * 1000, 3), "n": int(r4.nobs),
            "p": round(r4.pvalues["log_disbursements"], 4)}
    print(f"unique-URL attention: N = {int(r4.nobs)}  beta_hat (per 1,000) = {r4.params['log_disbursements'] * 1000:.6f}  "
          f"HC3 SE (per 1,000) = {r4.bse['log_disbursements'] * 1000:.6f}  p = {r4.pvalues['log_disbursements']:.6f}")
    for k, v in BASE_T4.items():
        ok = got4[k] == v
        print(f"  {k}: expected {v}, got {got4[k]}: {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"attention {k}: expected {v}, got {got4[k]}")
    if fails:
        print("\nBASELINE CHECK FAILED, stopping. no model was run.")
        for f in fails:
            print(f"  - {f}")
        sys.exit(1)
    print("baselines: all match")


def main():
    sys.stdout = Tee(OUT / "log.txt")
    print("\n" + "=" * 72 + "\ngross aid, parts 2 to 4 (run_gross_aid.py)\n" + "=" * 72)
    print(f"SPEC.md sha-256: {hashlib.sha256((OUT / 'SPEC.md').read_bytes()).hexdigest()}")
    df = load()
    print(f"analysis file: N = {len(df)}")
    print("\ncountries with fewer than 5 years of us data:")
    print(df[df["n_years_us"] < 5][["ISO3", "country", "us_gross_mean", "n_years_us", "us_oda_disbursements",
                                    "days_to_first_article", "attention_share_unique"]].to_string(index=False))

    baselines(df)

    print("\n" + "-" * 72 + "\nPART 3: MODELS\n" + "-" * 72)
    net_s, gross_s, same_s = "net aid > 0", "gross aid > 0", "net sample (net aid > 0)"
    dn = df[df["net_sample"]]
    vol = ["log_total_articles_unique"]
    popgdp = ["log_pop", "log_gdp"]
    for aid, label, s in [("log_disbursements", NET_LABEL, net_s), ("log_us_gross", GROSS_LABEL, gross_s)]:
        print(f"\n{label}:")
        run_ols("G1", aid, label, s, df, "log_days")
        run_ols("G2", aid, label, s, df, "log_attention_share_unique")
        run_ols("G3", aid, label, s, df, "log_days", vol)
        run_ols("G4", aid, label, s, df, "log_attention_share_unique", vol)
        run_cox("G5 without volume", aid, label, s, df)
        run_cox("G5 with volume", aid, label, s, df, vol)
        run_nb("G6", aid, label, s, df)
        run_ols("G7 days", aid, label, s, df, "log_days", popgdp)
        run_ols("G7 attention", aid, label, s, df, "log_attention_share_unique", popgdp)

    print("\nG8: joint model, log us_gross + log dac_gross")
    for y in ["log_days", "log_attention_share_unique"]:
        res = ols_hc3(y, ["log_us_gross", "log_dac_gross"], df)
        reg = df[[y, "log_us_gross", "log_dac_gross"]].dropna()
        scale = 1000 if y == "log_attention_share_unique" else 1
        outcome = ATTN if scale == 1000 else DAYS
        for var, label in [("log_us_gross", GROSS_LABEL), ("log_dac_gross", DAC_LABEL)]:
            add("G8 joint", label, gross_s, outcome, int(res.nobs), res.params[var] * scale, "HC3",
                res.bse[var] * scale, res.pvalues[var], res.rsquared)
        r = reg["log_us_gross"].corr(reg["log_dac_gross"])
        w = res.wald_test("log_us_gross = 0, log_dac_gross = 0", use_f=False, scalar=True)
        print(f"  {y}: N = {len(reg)}; pearson r(log us_gross, log dac_gross) = {r:.4f}; VIF = {1 / (1 - r ** 2):.4f}; "
              f"joint HC3 wald test both = 0: chi2(2) = "
              f"{float(w.statistic):.4f}, p = {float(w.pvalue):.6g}")

    print("\nG9: log us_share")
    run_ols("G9", "log_us_share", SHARE_LABEL, gross_s, df, "log_days")
    run_ols("G9", "log_us_share", SHARE_LABEL, gross_s, df, "log_attention_share_unique")

    print("\nnegative-aid check:")
    for y, name in [("log_days", "days"), ("log_attention_share_unique", "attention")]:
        n_net = df[[y, "log_disbursements"]].dropna()
        n_gross = df[[y, "log_us_gross"]].dropna()
        extra = df.loc[n_gross.index.difference(n_net.index)]
        print(f"  {name}: net sample N = {len(n_net)}, gross sample N = {len(n_gross)}; "
              f"in gross but not in net: {', '.join(extra['ISO3'])}")
    extra = df[~df["net_sample"] & df["log_us_gross"].notna()]
    print(extra[["ISO3", "country", "us_oda_disbursements", "us_gross_mean", "dac_gross_mean", "us_share",
                 "days_to_first_article", "attention_share_unique"]].to_string(index=False))
    print(f"\nG1 to G4 with gross aid on the net sample (N countries = {len(dn)}):")
    run_ols("G1", "log_us_gross", GROSS_LABEL, same_s, dn, "log_days")
    run_ols("G2", "log_us_gross", GROSS_LABEL, same_s, dn, "log_attention_share_unique")
    run_ols("G3", "log_us_gross", GROSS_LABEL, same_s, dn, "log_days", vol)
    run_ols("G4", "log_us_gross", GROSS_LABEL, same_s, dn, "log_attention_share_unique", vol)

    # part 4: outputs
    res = pd.DataFrame(ROWS)
    res.to_csv(OUT / "results.csv", index=False)
    print(f"\nwrote results.csv: {len(res)} rows")

    side = []
    keys = ["G1", "G2", "G3", "G4", "G5 without volume", "G5 with volume", "G6", "G7 days", "G7 attention"]
    for k in keys:
        net = res[(res["model"] == k) & (res["aid_variable"] == NET_LABEL)].iloc[0]
        gr = res[(res["model"] == k) & (res["aid_variable"] == GROSS_LABEL) & (res["sample"] == gross_s)].iloc[0]
        gs = res[(res["model"] == k) & (res["aid_variable"] == GROSS_LABEL) & (res["sample"] == same_s)]
        row = {"model": k, "outcome": net["outcome"], "se_type": net["se_type"]}
        for pre, r in [("net", net), ("gross", gr)] + ([("gross_on_net_sample", gs.iloc[0])] if len(gs) else []):
            for c in ["N", "beta_hat", "se", "p", "r2"]:
                row[f"{pre}_{c}"] = r[c]
        row["sign_match_gross"] = bool(np.sign(net["beta_hat"]) == np.sign(gr["beta_hat"]))
        if len(gs):
            row["sign_match_gross_on_net_sample"] = bool(np.sign(net["beta_hat"]) == np.sign(gs.iloc[0]["beta_hat"]))
        row["note"] = NOTE
        side.append(row)
    side = pd.DataFrame(side)
    order = (["model", "outcome", "se_type"]
             + [f"{p}_{c}" for p in ["net", "gross", "gross_on_net_sample"] for c in ["N", "beta_hat", "se", "p", "r2"]]
             + ["sign_match_gross", "sign_match_gross_on_net_sample", "note"])
    side = side[order]
    side.to_csv(OUT / "side_by_side.csv", index=False)
    print(f"wrote side_by_side.csv: {len(side)} rows")
    print(f"models run: {res.groupby(['model', 'aid_variable', 'sample', 'outcome'], sort=False).ngroups - 2} "
          f"(results.csv has {len(res)} rows; G8 has 2 rows per model)")


if __name__ == "__main__":
    main()
