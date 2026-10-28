# gdp fix step 4: markdown tables for REPORT.md, made from the step 3 csv files (no new computation)
# reads: outputs/gdp_fix/table1_old_new.csv, ratio_changes.csv, models_old_new.csv, conversion_factors.csv
# writes: outputs/gdp_fix/report_tables.md (stops if it exists)
import pandas as pd

from common import ROOT, OUT, out_path


def p_fmt(p):
    return f"{p:.2e}" if p < 0.001 else f"{p:.4f}"


def md(df):
    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.values) + "\n"


def main():
    path = out_path("report_tables.md")
    parts = []

    t1 = pd.read_csv(OUT / "table1_old_new.csv")
    t = t1.assign(**{c: t1[c].map(lambda x: f"{x:.2f}") for c in ["mean", "s", "min", "max"]})
    parts.append("### Table 1 rows, all versions (percent; s = sample standard deviation, ddof = 1)\n\n" + md(
        t[["variable", "version", "N", "mean", "s", "min", "max", "min_country", "max_country"]]))

    f = pd.read_csv(OUT / "conversion_factors.csv")
    parts.append("### Conversion factors f_t = Q_t / V_t (recipient DPGC, developing countries total)\n\n" + md(
        f[["year", "Q_usa", "V_usa", "f_usa", "f_usa_recipient_min", "f_usa_recipient_max", "f_dac",
           "f_dac_recipient_min", "f_dac_recipient_max"]].round(4)))

    rc = pd.read_csv(OUT / "ratio_changes.csv")
    for col, name in [("us_gdp", "US ODA / GDP"), ("dac_gdp", "DAC ODA / GDP")]:
        top = rc.reindex(rc[f"{col}_change_pp"].abs().sort_values(ascending=False).index).head(10)
        top = pd.DataFrame({"ISO3": top["ISO3"], "GDP years": top["n_years_gdp"],
                            "old %": top[f"{col}_old_pct"].round(3), "new %": top[f"{col}_new_pct"].round(3),
                            "change (pp)": top[f"{col}_change_pp"].round(3),
                            "change (relative)": (top[f"{col}_change_rel"] * 100).round(1).astype(str) + "%"})
        parts.append(f"### 10 largest absolute changes, {name}\n\n" + md(top))
    yc = rc[rc["ISO3"].isin(["YEM", "CUB"])]
    rows = []
    for _, r in yc.iterrows():
        for col, name in [("us_gdp", "US"), ("dac_gdp", "DAC")]:
            rows.append([r["ISO3"], int(r["n_years_gdp"]), name, f"{r[f'{col}_old_pct']:.4f}", f"{r[f'{col}_new_pct']:.4f}",
                         f"{r[f'{col}_change_rel'] * 100:.1f}%", f"{r[f'{col}_dacf_pct']:.4f}", f"{r[f'{col}_cur_pct']:.4f}"])
    parts.append("### YEM and CUB (percent)\n\n" + md(pd.DataFrame(rows, columns=[
        "ISO3", "GDP years", "row", "old", "new (US factor)", "relative change", "DAC factor", "current-price route"])))

    m = pd.read_csv(OUT / "models_old_new.csv")
    out = pd.DataFrame({"model": m["model"], "variant": m["variant"], "outcome": m["outcome"], "term": m["term"],
                        "N": m["N_old"].astype(str) + " / " + m["N_new"].astype(str),
                        "beta_hat old / new": m["beta_hat_old"].map("{:+.4f}".format) + " / " + m["beta_hat_new"].map("{:+.4f}".format),
                        "HC3 se old / new": m["se_old"].map("{:.4f}".format) + " / " + m["se_new"].map("{:.4f}".format),
                        "p old / new": m["p_old"].map(p_fmt) + " / " + m["p_new"].map(p_fmt),
                        "R2 old / new": m["r2_old"].map("{:.4f}".format) + " / " + m["r2_new"].map("{:.4f}".format)})
    parts.append("### Models that use GDP (OLS, HC3 standard errors; attention beta_hat and se x 1,000)\n\n" + md(out))

    path.write_text("\n".join(parts))
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
