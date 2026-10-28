# gdp fix step 3: table 1 aid / gdp rows and the gdp models (g7, b3 g8, b3 g9), old gdp (current usd)
#   vs new gdp (constant 2024 usd, us factor), plus the dac-factor and current-price cross-checks
# reads: the inputs of common.load(), outputs/gdp_fix/gdp_constant_2024.csv, oda_current_by_year.csv
# writes: outputs/gdp_fix/table1_old_new.csv, ratio_changes.csv, models_old_new.csv, crosscheck.csv
#   (stops if one exists)
import numpy as np
import pandas as pd

from common import ROOT, OUT, DAYS, load, table1_row, gdp_models, out_path

YEARS = [2018, 2019, 2020, 2021, 2022]
ROWS = [("us_gdp", "gross us oda / gdp, percent"), ("dac_gdp", "gross dac oda / gdp, percent")]


def gdp_frame(gc, col):
    return gc[["ISO3", col]].rename(columns={col: "gdp_avg"})


def current_price_ratio(df, oda, gdp):
    # cross-check 2: per year, aid at current prices / current gdp; mean over the years with gdp.
    # a missing aid year counts as 0 (same rule as aid_gross_2018_2022.csv)
    long = gdp.melt(id_vars="ISO3", value_vars=[f"gdp_current_{y}" for y in YEARS], var_name="year", value_name="gdp")
    long["year"] = long["year"].str[-4:].astype(int)
    long = long.dropna(subset=["gdp"]).merge(oda, on=["ISO3", "year"], how="left")
    out = df[["ISO3"]].copy()
    for donor, new in [("us_gross_current", "us_gdp"), ("dac_gross_current", "dac_gdp")]:
        long[new] = long[donor].fillna(0) * 1_000_000 / long["gdp"]
        out = out.merge(long.groupby("ISO3")[new].mean().reset_index(), on="ISO3", how="left")
    return out


def main():
    paths = {n: out_path(f"{n}.csv") for n in ["table1_old_new", "ratio_changes", "models_old_new", "crosscheck"]}
    gc = pd.read_csv(OUT / "gdp_constant_2024.csv")
    old = load()
    new = load(gdp_frame(gc, "gdp_const_avg"))
    dacf = load(gdp_frame(gc, "gdp_const_avg_dac"))
    oda = pd.read_csv(OUT / "oda_current_by_year.csv")
    cur = current_price_ratio(old, oda, gc)

    # table 1, old vs new, and the two cross-checks
    t1 = []
    for col, name in ROWS:
        for version, d in [("old: current usd gdp", old), ("new: constant 2024 usd gdp, us factor", new),
                           ("cross-check 1: constant 2024 usd gdp, dac factor", dacf),
                           ("cross-check 2: current aid / current gdp by year, mean", cur)]:
            t1.append({"variable": name, "version": version, **table1_row(d, col)})
    t1 = pd.DataFrame(t1)
    print("TABLE 1 (percent, s with ddof = 1)")
    print(t1.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    t1.to_csv(paths["table1_old_new"], index=False)

    # per-country ratio changes
    rc = old[["ISO3", "country"]].merge(gc[["ISO3", "n_years_gdp"]], on="ISO3", how="left")
    for col, _ in ROWS:
        rc[f"{col}_old_pct"] = old[col] * 100
        rc[f"{col}_new_pct"] = new[col] * 100
        rc[f"{col}_dacf_pct"] = dacf[col] * 100
        rc[f"{col}_cur_pct"] = cur[col].values * 100
        rc[f"{col}_change_pp"] = rc[f"{col}_new_pct"] - rc[f"{col}_old_pct"]
        rc[f"{col}_change_rel"] = rc[f"{col}_new_pct"] / rc[f"{col}_old_pct"] - 1
    rc.to_csv(paths["ratio_changes"], index=False)
    for col, name in ROWS:
        top = rc.reindex(rc[f"{col}_change_pp"].abs().sort_values(ascending=False).index).head(10)
        print(f"\n10 largest absolute changes, {name}")
        print(top[["ISO3", "n_years_gdp", f"{col}_old_pct", f"{col}_new_pct", f"{col}_change_pp", f"{col}_change_rel"]]
              .to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nrelative change (new / old - 1) by number of gdp years:")
    print(rc.groupby("n_years_gdp")["us_gdp_change_rel"].agg(["count", "min", "max"]).to_string())
    print("\nYEM and CUB:")
    print(rc[rc["ISO3"].isin(["YEM", "CUB"])].T.to_string())

    # models
    mo, mn = gdp_models(old), gdp_models(new)
    keys = ["model", "variant", "outcome", "term"]
    m = mo.merge(mn, on=keys + ["se_type"], suffixes=("_old", "_new"))
    m["sign_same"] = np.sign(m["beta_hat_old"]) == np.sign(m["beta_hat_new"])
    for a in [0.05, 0.10]:
        m[f"same_side_p{a:.2f}"] = (m["p_old"] < a) == (m["p_new"] < a)
    m["outcome"] = np.where(m["outcome"] == DAYS, "log(1 + days)", "log(1 + attention share), x1000")
    m.to_csv(paths["models_old_new"], index=False)
    print("\nMODELS (OLS, HC3 se)")
    for _, r in m.iterrows():
        print(f"  {r['model']:<16} | {r['variant']:<27} | {r['outcome'][:14]:<14} | {r['term']:<17} | "
              f"N {r['N_old']}->{r['N_new']} | b {r['beta_hat_old']:+.4f}->{r['beta_hat_new']:+.4f} | "
              f"se {r['se_old']:.4f}->{r['se_new']:.4f} | p {r['p_old']:.4f}->{r['p_new']:.4f} | "
              f"R2 {r['r2_old']:.4f}->{r['r2_new']:.4f}")

    # cross-check summary: primary vs dac factor vs current-price route, per country
    cc = []
    for col, name in ROWS:
        a, b, c = rc[f"{col}_new_pct"], rc[f"{col}_dacf_pct"], rc[f"{col}_cur_pct"]
        ok = a.notna() & c.notna()
        rel_b = (b / a - 1)[ok]
        rel_c = (c / a - 1)[ok & (a > 0)]
        cc.append({"variable": name, "N": int(ok.sum()),
                   "dac_factor_rel_diff_median": rel_b.median(), "dac_factor_rel_diff_min": rel_b.min(),
                   "dac_factor_rel_diff_max": rel_b.max(),
                   "current_route_rel_diff_median": rel_c.median(), "current_route_abs_rel_diff_median": rel_c.abs().median(),
                   "current_route_rel_diff_min": rel_c.min(), "current_route_rel_diff_max": rel_c.max(),
                   "current_route_rel_diff_min_country": rc.loc[rel_c.idxmin(), "ISO3"],
                   "current_route_rel_diff_max_country": rc.loc[rel_c.idxmax(), "ISO3"],
                   "pearson_r_log_primary_vs_current": np.corrcoef(np.log(a[ok & (a > 0)]), np.log(c[ok & (a > 0)]))[0, 1]})
    cc = pd.DataFrame(cc)
    print("\nCROSS-CHECKS (relative difference vs the primary new ratio)")
    print(cc.T.to_string())
    cc.to_csv(paths["crosscheck"], index=False)
    for p in paths.values():
        print(f"wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
