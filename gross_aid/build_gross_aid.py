# gross aid: merge oecd gross us and dac oda (2018-2022 mean) onto the 102 sample countries
# reads: data/raw/oecd_gross_us_2018_2022.csv, data/raw/oecd_gross_dac_2018_2022.csv,
#   data/input/3-29-v2_oda_data.csv, data/input/country-codes.csv
# writes: data/intermediate/aid_gross_2018_2022.csv and log.txt in this folder (run this before run_gross_aid.py)
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# import config.py from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

OUT = Path(__file__).resolve().parent
US_FILE = config.RAW_DIR / "oecd_gross_us_2018_2022.csv"
DAC_FILE = config.RAW_DIR / "oecd_gross_dac_2018_2022.csv"
OUT_FILE = config.INTERMEDIATE_DIR / "aid_gross_2018_2022.csv"
YEARS = [2018, 2019, 2020, 2021, 2022]

# expected value of each metadata column
EXPECTED = {"MEASURE": 240, "PRICE_BASE": "Q", "BASE_PER": 2024, "UNIT_MULT": 6, "FLOW_TYPE": "D"}

# (iso3, column, expected value), tolerance 0.01 usd million
SANITY = [("UKR", "us_gross_mean", 2187.07), ("UKR", "dac_gross_mean", 4563.85),
          ("KEN", "us_gross_mean", 831.69), ("EGY", "us_gross_mean", 213.88),
          ("GAB", "us_gross_mean", 1.589), ("GAB", "dac_gross_mean", 124.76)]
TOL = 0.01


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


def stop(failures):
    print("\nCHECKS FAILED, stopping. nothing was written to data/intermediate/.")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)


def check_file(d, donor, name):
    fails = []
    print(f"\n{name}: rows N = {len(d)}, recipients N = {d['RECIPIENT'].nunique()}")
    for col, val in {"DONOR": donor, **EXPECTED}.items():
        if col not in d.columns:
            fails.append(f"{name}: column {col} is missing")
            continue
        seen = sorted(d[col].astype(str).unique())
        ok = seen == [str(val)]
        print(f"  {col}: values {seen}, expected {val}: {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"{name}: {col} has {seen}, expected {val}")
    years = sorted(d["TIME_PERIOD"].unique())
    ok = set(years) <= set(YEARS)
    print(f"  TIME_PERIOD: {years}, expected only 2018 to 2022: {'ok' if ok else 'FAIL'}")
    print(f"  rows per year: {d['TIME_PERIOD'].value_counts().sort_index().to_dict()}")
    if not ok:
        fails.append(f"{name}: years {years}")
    n_na = int(d["OBS_VALUE"].isna().sum())
    n_neg = int((d["OBS_VALUE"] < 0).sum())
    print(f"  OBS_VALUE missing N = {n_na}, negative N = {n_neg}: {'ok' if n_na == 0 and n_neg == 0 else 'FAIL'}")
    if n_na or n_neg:
        fails.append(f"{name}: {n_na} missing and {n_neg} negative OBS_VALUE")
    n_dup = int(d.duplicated(["RECIPIENT", "TIME_PERIOD"]).sum())
    print(f"  duplicate (recipient, year) rows N = {n_dup}: {'ok' if n_dup == 0 else 'FAIL'}")
    if n_dup:
        fails.append(f"{name}: {n_dup} duplicate (recipient, year) rows")
    return fails


def mean_5y(d, prefix):
    # sum over the 5 years / 5, a missing year counts as 0
    g = d.groupby("RECIPIENT")["OBS_VALUE"].agg(["sum", "count"]).reset_index()
    g[f"{prefix}_gross_mean"] = g["sum"] / len(YEARS)
    g[f"n_years_{prefix}"] = g["count"]
    return g.rename(columns={"RECIPIENT": "iso3"})[["iso3", f"{prefix}_gross_mean", f"n_years_{prefix}"]]


def main():
    sys.stdout = Tee(OUT / "log.txt")
    print("gross aid, part 1: merge (build_gross_aid.py)")

    us = pd.read_csv(US_FILE)
    dac = pd.read_csv(DAC_FILE)
    fails = check_file(us, "USA", "us file") + check_file(dac, "DAC", "dac file")

    # us <= dac for every (recipient, year) in the us file
    both = us[["RECIPIENT", "TIME_PERIOD", "OBS_VALUE"]].merge(
        dac[["RECIPIENT", "TIME_PERIOD", "OBS_VALUE"]], on=["RECIPIENT", "TIME_PERIOD"],
        how="left", suffixes=("_us", "_dac"))
    no_dac = both[both["OBS_VALUE_dac"].isna()]
    over = both[both["OBS_VALUE_us"] > both["OBS_VALUE_dac"]]
    print(f"\nus <= dac check: us (recipient, year) rows N = {len(both)}; "
          f"with no dac row N = {len(no_dac)}; with us > dac N = {len(over)}")
    if len(no_dac):
        print(no_dac.to_string(index=False))
        fails.append(f"{len(no_dac)} us (recipient, year) rows have no dac row")
    if len(over):
        print(over.to_string(index=False))
        fails.append(f"{len(over)} us (recipient, year) rows have us > dac")
    if fails:
        stop(fails)

    # sample: the 102 countries of the main analysis file, net aid unchanged
    base = pd.read_csv(config.ODA_DATA)
    base["iso3"] = base["ISO3"].astype(str).str.strip().str.upper()
    base["us_net"] = pd.to_numeric(base["us_oda_disbursements"].astype(str).str.replace(",", ""), errors="coerce")
    base = base[["iso3", "country", "us_net"]]
    print(f"\nsample file: N = {len(base)}")

    # recipient codes that do not join to the sample
    cc = pd.read_csv(config.COUNTRY_CODES, dtype=str)
    iso_all = set(cc["ISO3166-1-Alpha-3"].dropna().str.strip().str.upper())
    names = pd.concat([us, dac])[["RECIPIENT", "Recipient"]].drop_duplicates("RECIPIENT").set_index("RECIPIENT")["Recipient"]
    codes = sorted(set(us["RECIPIENT"]) | set(dac["RECIPIENT"]))
    dropped = [c for c in codes if c not in set(base["iso3"])]
    agg = [c for c in dropped if c not in iso_all]
    other = [c for c in dropped if c in iso_all]
    print(f"recipient codes in the oecd files N = {len(codes)}; joined to the sample N = {len(codes) - len(dropped)}; "
          f"dropped N = {len(dropped)}")
    print(f"dropped, not an iso3 code in country-codes.csv (aggregates and other codes), N = {len(agg)}:")
    for c in agg:
        print(f"  {c}  {names[c]}")
    print(f"dropped, iso3 country not in the 102-country sample, N = {len(other)}:")
    print("  " + ", ".join(other))

    # 5-year means
    us_m = mean_5y(us, "us")
    dac_m = mean_5y(dac, "dac")
    d = base.merge(us_m, on="iso3", how="left").merge(dac_m, on="iso3", how="left")
    no_us = d[d["us_gross_mean"].isna()]
    no_dac_row = d[d["dac_gross_mean"].isna()]
    for c in ["us_gross_mean", "dac_gross_mean"]:
        d[c] = d[c].fillna(0.0)  # no row at all = 5 missing years = 0
    for c in ["n_years_us", "n_years_dac"]:
        d[c] = d[c].fillna(0).astype(int)
    d["us_share"] = np.where(d["dac_gross_mean"] > 0, d["us_gross_mean"] / d["dac_gross_mean"], np.nan)
    print(f"\nmerged: N = {len(d)}")

    print(f"\nsample countries with no row in the us file, N = {len(no_us)}: "
          f"{', '.join(no_us['iso3'] + ' ' + no_us['country']) or 'none'}")
    print(f"sample countries with no row in the dac file, N = {len(no_dac_row)}: "
          f"{', '.join(no_dac_row['iso3']) or 'none'}")
    few = d[(d["n_years_us"] < 5) | (d["n_years_dac"] < 5)]
    print(f"sample countries with fewer than 5 years (us or dac), N = {len(few)}:")
    if len(few):
        print(few[["iso3", "country", "n_years_us", "n_years_dac", "us_gross_mean", "dac_gross_mean"]].to_string(index=False))
    gt1 = d[d["us_share"] > 1]
    print(f"sample countries with us_share > 1, N = {len(gt1)}: {', '.join(gt1['iso3']) or 'none'}")
    nonpos = d[d["dac_gross_mean"] <= 0]
    print(f"sample countries with dac_gross_mean <= 0, N = {len(nonpos)}: {', '.join(nonpos['iso3']) or 'none'}")

    # sanity values
    print("\nsanity values (tolerance 0.01 usd million):")
    for iso, col, val in SANITY:
        got = d.loc[d["iso3"] == iso, col]
        got = float(got.iloc[0]) if len(got) else np.nan
        ok = abs(got - val) <= TOL
        print(f"  {iso} {col}: expected {val}, got {got:.4f}, diff {got - val:+.4f}: {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"sanity {iso} {col}: expected {val}, got {got:.4f}")
    if fails:
        stop(fails)

    # gross vs net
    cmp_ = d.dropna(subset=["us_net"])
    rho, rho_p = stats.spearmanr(cmp_["us_gross_mean"], cmp_["us_net"])
    pos = cmp_[cmp_["us_net"] > 0]
    ratio = (pos["us_gross_mean"] / pos["us_net"]).median()
    print(f"\ngross vs net: N with a net value = {len(cmp_)}")
    print(f"  spearman rho = {rho:.4f} (p = {rho_p:.3g}), N = {len(cmp_)}")
    print(f"  median ratio gross / net (net > 0) = {ratio:.4f}, N = {len(pos)}")
    lower = cmp_[cmp_["us_gross_mean"] < cmp_["us_net"]]
    print(f"  countries with gross < net, N = {len(lower)}:")
    if len(lower):
        print(lower[["iso3", "country", "us_gross_mean", "us_net"]].to_string(index=False))
    print("  the base year of the net sheet is not known, so levels may differ by a constant.")

    cols = ["iso3", "country", "us_gross_mean", "n_years_us", "dac_gross_mean", "n_years_dac", "us_share", "us_net"]
    d[cols].to_csv(OUT_FILE, index=False)
    print(f"\nwrote {OUT_FILE.relative_to(config.ROOT)}: N = {len(d)}")
    print("part 1: all checks passed")


if __name__ == "__main__":
    main()
