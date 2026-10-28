# gdp fix step 1: reproduce the current table 1 aid / gdp rows and the g7, b3 g8 and b3 g9 results
#   with the snapshot gdp_avg (current usd), before anything is changed
# reads: the inputs of common.load(), gross_aid/results.csv, gross_aid/followup/results.csv
# writes: outputs/gdp_fix/reproduce_current.csv (stops if it exists, or if a value does not match)
import sys

import pandas as pd

from common import ROOT, DAYS, load, table1_row, gdp_models, out_path

TOL = 1e-9
# draft table 1, percent: (column, N, mean, s, min, max)
DRAFT = [("us_gdp", 100, "1.16", "3.00", "0.00", "26.89"), ("dac_gdp", 100, "2.92", "4.52", "0.03", "30.54")]
# followup model name for each (model, variant, term) of common.gdp_models()
FOLLOWUP = {("G8", "B3 levels on the gdp sample", "log_us_gross"): "G8 log us_gross",
            ("G8", "B3 levels on the gdp sample", "log_dac_gross"): "G8 log dac_gross",
            ("G8", "B3 aid / gdp", "log_us_gdp"): "G8 log us_gross/gdp",
            ("G8", "B3 aid / gdp", "log_dac_gdp"): "G8 log dac_gross/gdp",
            ("G9 log us_share", "B3 aid / gdp", "log_us_share"): "G9 log us_share",
            ("G9 ratio", "B3 aid / gdp", "log_us_gdp"): "G9 ratio log us_gross/gdp"}
G7_LABEL = {"net": "US aid (USD millions) (net)", "gross": "US aid (USD millions) (gross)"}


def main():
    path = out_path("reproduce_current.csv")
    df = load()
    fails, out = [], []

    print("table 1 aid / gdp rows (percent, s with ddof = 1)")
    for col, n, mean, s, lo, hi in DRAFT:
        r = table1_row(df, col)
        got = (r["N"], f"{r['mean']:.2f}", f"{r['s']:.2f}", f"{r['min']:.2f}", f"{r['max']:.2f}")
        ok = got == (n, mean, s, lo, hi)
        print(f"  {col}: got {got}, expected {(n, mean, s, lo, hi)}: {'ok' if ok else 'FAIL'}; "
              f"min {r['min_country']}, max {r['max_country']}")
        out.append({"item": f"table 1 {col}", "expected": str((n, mean, s, lo, hi)), "got": str(got), "match": ok})
        fails += [] if ok else [col]

    print("\nmodels (HC3), against the results files")
    gross = pd.read_csv(ROOT / "gross_aid" / "results.csv")
    follow = pd.read_csv(ROOT / "gross_aid" / "followup" / "results.csv")
    mods = gdp_models(df)
    for _, r in mods.iterrows():
        if r["model"].startswith("G7"):
            if r["term"] not in ("log_disbursements", "log_us_gross"):
                continue  # results.csv keeps only the aid coefficient
            ref = gross[(gross["model"] == r["model"]) & (gross["aid_variable"] == G7_LABEL[r["variant"]])]
            src = "gross_aid/results.csv"
        else:
            name = FOLLOWUP[(r["model"], r["variant"], r["term"])]
            out_name = "log(1 + days to first article)" if r["outcome"] == DAYS else None
            ref = follow[(follow["model"] == name) & (follow["variant"] == r["variant"])]
            ref = ref[ref["outcome"] == out_name] if out_name else ref[ref["outcome"].str.startswith("log(1 + unique")]
            src = "gross_aid/followup/results.csv"
        ref = ref.iloc[0]
        diffs = {c: abs(r[c] - ref[c]) for c in ["beta_hat", "se", "p", "r2"]}
        ok = int(ref["N"]) == r["N"] and max(diffs.values()) < TOL
        print(f"  {r['model']:<16} | {r['variant']:<27} | {r['outcome']:<26} | {r['term']:<17} | N {r['N']:>3} | "
              f"beta_hat {r['beta_hat']:+.6f} | HC3 se {r['se']:.6f} | p {r['p']:.6f} | R2 {r['r2']:.6f} | "
              f"max abs diff {max(diffs.values()):.1e}: {'ok' if ok else 'FAIL'}")
        out.append({"item": f"{r['model']} | {r['variant']} | {r['outcome']} | {r['term']}", "expected": src,
                    "got": f"N {r['N']}, beta_hat {r['beta_hat']:.6f}, se {r['se']:.6f}, p {r['p']:.6g}, "
                           f"r2 {r['r2']:.6f}", "match": ok})
        fails += [] if ok else [out[-1]["item"]]

    pd.DataFrame(out).to_csv(path, index=False)
    print(f"\nwrote {path.relative_to(ROOT)}")
    if fails:
        print("STOP: these do not match:\n  " + "\n  ".join(fails))
        sys.exit(1)
    print("all match")


if __name__ == "__main__":
    main()
