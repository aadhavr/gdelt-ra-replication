# gdp fix, final: aid / gdp = current-price gross oda / current-price gdp per year, mean over 2018-2022.
#   checks first (stops on any failure), then table 1 rows and the b3 g8 / g9 reruns; g7 is checked unchanged
# reads: the inputs of common.load(), outputs/gdp_fix/wdi_gdp_current_2018_2022.csv, oda_current_by_year.csv,
#   table1_old_new.csv, models_old_new.csv, gross_aid/results.csv, gross_aid/followup/results.csv
# writes: outputs/gdp_fix/table1_final.csv, models_final.csv, final_tables.md (stops if one exists)
import sys

import numpy as np
import pandas as pd

from common import ROOT, OUT, DAYS, load, table1_row, gdp_models, out_path
from compare_old_new import current_price_ratio, ROWS
from reproduce_current import DRAFT, FOLLOWUP, G7_LABEL

TOL = 1e-9
FAILS = []


def check(name, ok, detail=""):
    print(f"  {name}: {'ok' if ok else 'FAIL'} {detail}")
    if not ok:
        FAILS.append(name)


def p_fmt(p):
    return f"{p:.2e}" if p < 0.001 else f"{p:.4f}"


def md(df):
    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.values) + "\n"


def ref_row(r, gross, follow):
    # the stored result for one row of common.gdp_models()
    if r["model"].startswith("G7"):
        return gross[(gross["model"] == r["model"]) & (gross["aid_variable"] == G7_LABEL[r["variant"]])].iloc[0]
    ref = follow[(follow["model"] == FOLLOWUP[(r["model"], r["variant"], r["term"])]) & (follow["variant"] == r["variant"])]
    days = ref["outcome"] == "log(1 + days to first article)"
    return ref[days if r["outcome"] == DAYS else ~days].iloc[0]


def main():
    paths = {n: out_path(n) for n in ["table1_final.csv", "models_final.csv", "final_tables.md"]}
    old = load()
    gc = pd.read_csv(OUT / "wdi_gdp_current_2018_2022.csv")
    oda = pd.read_csv(OUT / "oda_current_by_year.csv")
    cur = current_price_ratio(old, oda, gc)
    fin = old.drop(columns=["us_gdp", "dac_gdp"]).merge(cur, on="ISO3", how="left")  # gdp_avg and log_gdp unchanged
    first = pd.read_csv(OUT / "table1_old_new.csv")
    gross = pd.read_csv(ROOT / "gross_aid" / "results.csv")
    follow = pd.read_csv(ROOT / "gross_aid" / "followup" / "results.csv")

    print("CHECKS")
    # 1. old table 1 rows reproduce the draft
    for col, n, mean, s, lo, hi in DRAFT:
        r = table1_row(old, col)
        got = (r["N"], f"{r['mean']:.2f}", f"{r['s']:.2f}", f"{r['min']:.2f}", f"{r['max']:.2f}")
        check(f"old table 1 {col}", got == (n, mean, s, lo, hi), str(got))
    # 2. the current-price ratio reproduces cross-check 2 of the first run
    stats = ["N", "mean", "s", "min", "max"]
    for col, name in ROWS:
        r = table1_row(fin, col)
        ref = first[(first["variable"] == name) & first["version"].str.startswith("cross-check 2")].iloc[0]
        diff = max(abs(r[k] - ref[k]) for k in stats)
        check(f"current-price {col} vs first run", diff < 1e-12 and r["min_country"] == ref["min_country"]
              and r["max_country"] == ref["max_country"], f"max abs diff {diff:.1e}")
    # 3. old models (snapshot gdp) reproduce the results files; 4. g7 in the final setup is unchanged
    mo, mf = gdp_models(old), gdp_models(fin)
    for _, r in mo.iterrows():
        if r["model"].startswith("G7") and r["term"] not in ("log_disbursements", "log_us_gross"):
            continue
        ref = ref_row(r, gross, follow)
        diff = max(abs(r[c] - ref[c]) for c in ["beta_hat", "se", "p", "r2"])
        check(f"old {r['model']} {r['variant']} {r['outcome']} {r['term']}", int(ref["N"]) == r["N"] and diff < TOL,
              f"max abs diff {diff:.1e}")
    g7o, g7f = mo[mo["model"].str.startswith("G7")], mf[mf["model"].str.startswith("G7")]
    cols = ["N", "beta_hat", "se", "p", "r2"]
    diff = np.abs(g7o[cols].values - g7f[cols].values).max()
    check("g7 final setup equals g7 old (all 12 coefficients, incl. log_pop and log_gdp)", diff == 0, f"max abs diff {diff:.1e}")
    mon = pd.read_csv(OUT / "models_old_new.csv")
    g7m = mon[mon["model"].str.startswith("G7")]
    diff = np.abs(g7m[[f"{c}_old" for c in cols]].values - g7f[cols].values).max()
    check("g7 final setup equals the old columns of models_old_new.csv", diff < TOL, f"max abs diff {diff:.1e}")
    if FAILS:
        print("STOP: checks failed:\n  " + "\n  ".join(FAILS))
        sys.exit(1)
    print("all checks pass\n")

    # table 1: old, primary constant usd (first run), final
    t1 = []
    for col, name in ROWS:
        t1.append({"variable": name, "version": "old: current usd gdp", **table1_row(old, col)})
        ref = first[(first["variable"] == name) & first["version"].str.startswith("new:")].iloc[0]
        t1.append({"variable": name, "version": "first run primary: constant 2024 usd gdp, us factor",
                   **{k: ref[k] for k in stats + ["min_country", "max_country"]}})
        t1.append({"variable": name, "version": "final: current aid / current gdp per year, mean", **table1_row(fin, col)})
    t1 = pd.DataFrame(t1)
    t1["N"] = t1["N"].astype(int)
    print(t1.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    t1.to_csv(paths["table1_final.csv"], index=False)

    # b3 g8 and g9, old vs final (g7 and the sample-only b3 models included for completeness)
    keys = ["model", "variant", "outcome", "term", "se_type"]
    m = mo.merge(mf, on=keys, suffixes=("_old", "_new"))
    m["changed"] = (m[[f"{c}_old" for c in cols]].values != m[[f"{c}_new" for c in cols]].values).any(axis=1)
    m["sign_same"] = np.sign(m["beta_hat_old"]) == np.sign(m["beta_hat_new"])
    for a in [0.05, 0.10]:
        m[f"same_side_p{a:.2f}"] = (m["p_old"] < a) == (m["p_new"] < a)
    m["outcome"] = np.where(m["outcome"] == DAYS, "log(1 + days)", "log(1 + attention share), x1000")
    m.to_csv(paths["models_final.csv"], index=False)
    print("\nMODELS (OLS, HC3 se)")
    for _, r in m.iterrows():
        print(f"  {r['model']:<16} | {r['variant']:<27} | {r['outcome'][:14]:<14} | {r['term']:<17} | "
              f"N {r['N_old']}->{r['N_new']} | b {r['beta_hat_old']:+.4f}->{r['beta_hat_new']:+.4f} | "
              f"se {r['se_old']:.4f}->{r['se_new']:.4f} | p {p_fmt(r['p_old'])}->{p_fmt(r['p_new'])} | "
              f"R2 {r['r2_old']:.4f}->{r['r2_new']:.4f} | changed {r['changed']} | sign same {r['sign_same']} | "
              f"same side .05 {r['same_side_p0.05']} .10 {r['same_side_p0.10']}")

    # wald and collinearity for the new b3 g8, as run_followup.py joint()
    from common import b3_sample, ols_hc3
    for label, d in [("old", old), ("final", fin)]:
        d3 = b3_sample(d)
        for y in [DAYS, "log_attention_share_unique"]:
            res = ols_hc3(y, ["log_us_gdp", "log_dac_gdp"], d3)
            reg = d3[[y, "log_us_gdp", "log_dac_gdp"]].dropna()
            rr = reg["log_us_gdp"].corr(reg["log_dac_gdp"])
            w = res.wald_test("log_us_gdp = 0, log_dac_gdp = 0", use_f=False, scalar=True)
            print(f"  B3 G8 {label} {y}: r = {rr:.4f}, VIF = {1 / (1 - rr ** 2):.4f}, HC3 wald both = 0: "
                  f"chi2(2) = {float(w.statistic):.4f}, p = {float(w.pvalue):.6g}")

    # markdown tables for the report
    t = t1.copy()
    for c in ["mean", "s", "min", "max"]:
        t[c] = t[c].map(lambda x: f"{x:.2f}")
    b3 = m[m["variant"].str.startswith("B3")]
    mt = pd.DataFrame({"model": b3["model"], "variant": b3["variant"], "outcome": b3["outcome"], "term": b3["term"],
                       "N old / new": b3["N_old"].astype(str) + " / " + b3["N_new"].astype(str),
                       "beta_hat old / new": b3["beta_hat_old"].map("{:+.4f}".format) + " / " + b3["beta_hat_new"].map("{:+.4f}".format),
                       "HC3 se old / new": b3["se_old"].map("{:.4f}".format) + " / " + b3["se_new"].map("{:.4f}".format),
                       "p old / new": b3["p_old"].map(p_fmt) + " / " + b3["p_new"].map(p_fmt),
                       "R2 old / new": b3["r2_old"].map("{:.4f}".format) + " / " + b3["r2_new"].map("{:.4f}".format)})
    paths["final_tables.md"].write_text(
        "### Table 1 rows (percent, s with ddof = 1)\n\n" + md(t[["variable", "version", "N", "mean", "s", "min", "max",
                                                                   "min_country", "max_country"]])
        + "\n### B3 models (OLS, HC3 se; attention beta_hat and se x 1,000)\n\n" + md(mt))
    for p in paths.values():
        print(f"wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
