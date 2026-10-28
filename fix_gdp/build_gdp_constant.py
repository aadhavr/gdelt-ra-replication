# gdp fix step 2b to 2e: check the new oecd pull against aid_gross_2018_2022.csv, make the q / v
#   conversion factors, and build gdp in constant 2024 usd (us factor primary, dac factor cross-check)
# reads: data/raw_oecd_pull/dac2a_usa_dac_240_QV_2018_2022.csv, outputs/gdp_fix/wdi_gdp_current_2018_2022.csv,
#   data/intermediate/aid_gross_2018_2022.csv
# writes: outputs/gdp_fix/pull_check_yearly.csv, conversion_factors.csv, gdp_constant_2024.csv,
#   oda_current_by_year.csv (stops if one exists, or if the q pull does not reproduce the existing oecd data)
import sys

import pandas as pd

from common import ROOT, OUT, GROSS_FILE, out_path

PULL = ROOT / "data" / "raw_oecd_pull" / "dac2a_usa_dac_240_QV_2018_2022.csv"
YEARS = [2018, 2019, 2020, 2021, 2022]
TOTAL = "DPGC"  # recipient aggregate "Developing countries"


def main():
    paths = {n: out_path(f"{n}.csv") for n in ["pull_check_yearly", "conversion_factors", "gdp_constant_2024",
                                               "oda_current_by_year"]}
    raw = pd.read_csv(PULL)[["DONOR", "RECIPIENT", "PRICE_BASE", "TIME_PERIOD", "OBS_VALUE", "BASE_PER"]]
    q = raw[raw["PRICE_BASE"] == "Q"]
    print(f"pull: rows N = {len(raw)}; Q base period {q['BASE_PER'].unique().tolist()}")
    if raw.duplicated(["DONOR", "RECIPIENT", "PRICE_BASE", "TIME_PERIOD"]).any():
        sys.exit("STOP: duplicate rows in the pull.")

    # check 1: every yearly q value of the sample countries equals the existing data/raw file, bit for bit
    old = pd.read_csv(GROSS_FILE)
    rows, fails = [], []
    for donor, f, col, ncol in [("USA", "us", "us_gross_mean", "n_years_us"), ("DAC", "dac", "dac_gross_mean", "n_years_dac")]:
        o = pd.read_csv(ROOT / "data" / "raw" / f"oecd_gross_{f}_2018_2022.csv")[["RECIPIENT", "TIME_PERIOD", "OBS_VALUE"]]
        n = q[q["DONOR"] == donor][["RECIPIENT", "TIME_PERIOD", "OBS_VALUE"]]
        m = o.merge(n, on=["RECIPIENT", "TIME_PERIOD"], how="outer", suffixes=("_old", "_new"))
        m = m[m["RECIPIENT"].isin(old["iso3"])]
        same = (m["OBS_VALUE_old"] == m["OBS_VALUE_new"]).sum()
        print(f"  {donor}: sample country-year rows N = {len(m)}, bit-identical N = {same}")
        if same < len(m):
            fails.append(f"{donor} yearly values")
        # check 2: sum over years / 5 (as build_gross_aid.py mean_5y) against the existing file, tolerance 1e-12
        g = n.groupby("RECIPIENT")["OBS_VALUE"].agg(["sum", "count"])
        g["new"] = g["sum"] / len(YEARS)
        mm = old.set_index("iso3")[[col, ncol]].join(g)
        mm["new"], mm["count"] = mm["new"].fillna(0), mm["count"].fillna(0).astype(int)
        mm["abs_diff"] = (mm["new"] - mm[col]).abs()
        print(f"  {donor}: means exactly equal N = {(mm['new'] == mm[col]).sum()} of {len(mm)}, "
              f"max abs diff = {mm['abs_diff'].max():.3e}, n_years equal N = {(mm['count'] == mm[ncol]).sum()}")
        if mm["abs_diff"].max() > 1e-12 or (mm["count"] != mm[ncol]).any():
            fails.append(f"{donor} means")
        for iso, r in mm.iterrows():
            rows.append({"donor": donor, "iso3": iso, "old_mean": r[col], "new_mean": r["new"], "abs_diff": r["abs_diff"],
                         "exact": r["new"] == r[col], "old_n_years": r[ncol], "new_n_years": r["count"]})
    pd.DataFrame(rows).to_csv(paths["pull_check_yearly"], index=False)
    if fails:
        sys.exit("STOP: the q pull does not reproduce the existing data: " + ", ".join(fails))
    print("  q pull: yearly values bit-identical; means equal up to float summation order (<= 1e-12)")

    # factors f_t = Q_t / V_t on the donor total to developing countries
    w = raw.pivot_table(index=["DONOR", "RECIPIENT", "TIME_PERIOD"], columns="PRICE_BASE", values="OBS_VALUE").reset_index()
    w["f"] = w["Q"] / w["V"]
    tot = w[w["RECIPIENT"] == TOTAL]
    f = {d: tot[tot["DONOR"] == d].set_index("TIME_PERIOD")["f"].reindex(YEARS) for d in ["USA", "DAC"]}
    fac = pd.DataFrame({"year": YEARS, "Q_usa": tot[tot.DONOR == "USA"].set_index("TIME_PERIOD")["Q"].reindex(YEARS).values,
                        "V_usa": tot[tot.DONOR == "USA"].set_index("TIME_PERIOD")["V"].reindex(YEARS).values,
                        "f_usa": f["USA"].values,
                        "Q_dac": tot[tot.DONOR == "DAC"].set_index("TIME_PERIOD")["Q"].reindex(YEARS).values,
                        "V_dac": tot[tot.DONOR == "DAC"].set_index("TIME_PERIOD")["V"].reindex(YEARS).values,
                        "f_dac": f["DAC"].values})
    # spread of q / v over recipients (rows with v > 0), to show how uniform the factor is
    pos = w[w["V"] > 0]
    for d in ["USA", "DAC"]:
        sp = pos[pos["DONOR"] == d].groupby("TIME_PERIOD")["f"].agg(["min", "median", "max"]).reindex(YEARS)
        fac[f"f_{d.lower()}_recipient_min"] = sp["min"].values
        fac[f"f_{d.lower()}_recipient_median"] = sp["median"].values
        fac[f"f_{d.lower()}_recipient_max"] = sp["max"].values
    if fac[["f_usa", "f_dac"]].isna().any().any():
        sys.exit("STOP: a factor is missing.")
    print("\nfactors (recipient DPGC):")
    print(fac.to_string(index=False))
    fac.to_csv(paths["conversion_factors"], index=False)

    # gdp in constant 2024 usd: gdp_t x f_t, mean over the years with a value (as analysis.py)
    gdp = pd.read_csv(OUT / "wdi_gdp_current_2018_2022.csv")
    cur = [f"gdp_current_{y}" for y in YEARS]
    for d, suf in [("USA", ""), ("DAC", "_dac")]:
        for y in YEARS:
            gdp[f"f{suf or '_usa'}_{y}"] = f[d][y]
        gdp[f"gdp_const_avg{suf}"] = gdp[cur].mul(f[d].values, axis=1).mean(axis=1)  # skips missing years
    gdp = gdp.rename(columns={"gdp_avg_snapshot": "gdp_avg_old"})
    keep = (["ISO3", "country"] + cur + ["n_years_gdp"] + [f"f_usa_{y}" for y in YEARS] + ["gdp_const_avg", "gdp_avg_old",
            "gdp_current_avg"] + [f"f_dac_{y}" for y in YEARS] + ["gdp_const_avg_dac"])
    gdp = gdp[keep]
    gdp["ratio_const_to_old"] = gdp["gdp_const_avg"] / gdp["gdp_avg_old"]
    miss = gdp[gdp["gdp_const_avg"].isna()]
    print(f"\ngdp missing N = {len(miss)}: {', '.join(miss['ISO3'])}")
    few = gdp[(gdp["n_years_gdp"] > 0) & (gdp["n_years_gdp"] < 5)]
    print("fewer than 5 years: " + ", ".join(f"{i} ({n}: {', '.join(str(y) for y in YEARS if pd.notna(gdp.loc[gdp.ISO3 == i, f'gdp_current_{y}'].iloc[0]))})"
                                             for i, n in zip(few["ISO3"], few["n_years_gdp"])))
    r = gdp["ratio_const_to_old"].dropna()
    print(f"gdp_const_avg / gdp_avg_old: min {r.min():.6f}, median {r.median():.6f}, max {r.max():.6f}")
    gdp.to_csv(paths["gdp_constant_2024"], index=False)

    # cross-check 2 input: gross oda at current prices (v) by country and year, sample countries only
    v = raw[(raw["PRICE_BASE"] == "V") & raw["RECIPIENT"].isin(old["iso3"])]
    v = v.pivot_table(index=["RECIPIENT", "TIME_PERIOD"], columns="DONOR", values="OBS_VALUE").reset_index()
    v.columns = ["ISO3", "year", "dac_gross_current", "us_gross_current"]
    v.to_csv(paths["oda_current_by_year"], index=False)
    for p in paths.values():
        print(f"wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
