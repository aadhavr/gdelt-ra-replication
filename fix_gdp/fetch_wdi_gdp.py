# gdp fix step 2a: download yearly wdi NY.GDP.MKTP.CD (current usd) for 2018-2022 for the 102 sample
#   countries, and compare the mean with the snapshot gdp_avg
# reads: api.worldbank.org, data/input/3-29-v2_oda_data.csv, data/input/wdi_population_gdp.csv
# writes: outputs/gdp_fix/wdi_gdp_current_2018_2022.csv (stops if it exists)
import pandas as pd
import requests

from common import ROOT, ODA_DATA, WDI_SNAPSHOT, out_path

YEARS = [2018, 2019, 2020, 2021, 2022]


def fetch_wdi(indicator):
    # same request as robustness/analysis.py fetch_wdi()
    url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    params = {"date": "2018:2022", "format": "json", "per_page": 20000}
    r = requests.get(url, params=params, timeout=(10, 60))
    r.raise_for_status()
    payload = r.json()
    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError(f"unexpected wdi response shape for {indicator}")
    print(f"wdi {indicator}: records N = {len(payload[1])}, last updated {payload[0].get('lastupdated')}")
    return pd.DataFrame(payload[1])


def main():
    path = out_path("wdi_gdp_current_2018_2022.csv")
    raw = fetch_wdi("NY.GDP.MKTP.CD")
    raw["ISO3"] = raw["countryiso3code"].astype(str).str.strip().str.upper()
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    raw["year"] = pd.to_numeric(raw["date"], errors="coerce").astype(int)
    wide = raw.pivot_table(index="ISO3", columns="year", values="value", aggfunc="first")
    wide.columns = [f"gdp_current_{y}" for y in wide.columns]

    sample = pd.read_csv(ODA_DATA)[["ISO3", "country"]]
    sample["ISO3"] = sample["ISO3"].astype(str).str.strip().str.upper()
    df = sample.merge(wide.reset_index(), on="ISO3", how="left")
    cols = [f"gdp_current_{y}" for y in YEARS]
    df["n_years_gdp"] = df[cols].notna().sum(axis=1)
    df["gdp_current_avg"] = df[cols].mean(axis=1)  # mean of the years with a value, as in analysis.py
    snap = pd.read_csv(WDI_SNAPSHOT)[["ISO3", "gdp_avg"]].rename(columns={"gdp_avg": "gdp_avg_snapshot"})
    df = df.merge(snap, on="ISO3", how="left")
    df["rel_diff_vs_snapshot"] = df["gdp_current_avg"] / df["gdp_avg_snapshot"] - 1

    print(f"sample countries N = {len(df)}")
    print(f"years with gdp: {df['n_years_gdp'].value_counts().sort_index().to_dict()}")
    print("countries with fewer than 5 years: " + ", ".join(
        f"{i} ({n})" for i, n in zip(df.loc[df["n_years_gdp"] < 5, "ISO3"], df.loc[df["n_years_gdp"] < 5, "n_years_gdp"])))
    both = df.dropna(subset=["gdp_current_avg", "gdp_avg_snapshot"])
    rd = both["rel_diff_vs_snapshot"].abs()
    print(f"vs snapshot (N {len(both)}): exact equal N = {(both['gdp_current_avg'] == both['gdp_avg_snapshot']).sum()}, "
          f"max abs relative diff = {rd.max():.3e} ({both.loc[rd.idxmax(), 'ISO3']}), N with abs rel diff > 1e-6 = {(rd > 1e-6).sum()}")
    df.to_csv(path, index=False)
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
