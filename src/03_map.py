# maps each matched row to a country (fips -> iso2, mysociety/gaze) and a un region
# reads: data/intermediate/usaid_closure_v1/matches_rows.csv and a crosswalk from github
# writes: data/intermediate/usaid_final_geography.csv (date, url, country, region)
# no table uses this output. 04_build_dataset.py maps countries with country-codes.csv
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

import pandas as pd
import numpy as np
import country_converter as coco

# inputs and outputs
INPUT_CSV = config.MATCHES_ROWS
CROSSWALK_URL = "https://raw.githubusercontent.com/mysociety/gaze/master/data/fips-10-4-to-iso-country-codes.csv"

# names for two more outputs (this script does not write them)
OUT_EVENT_LEVEL = "usaid_country_region.csv"  # one row per event
OUT_COUNTRY_MAP = "usaid_country_region_mapping.csv"  # one row per country (optional but useful)

# load data
df = pd.read_csv(INPUT_CSV)
df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")

# gdelt actiongeo_countrycode (2-char fips 10-4)
df["country_fips"] = df["col_51"].astype(str).str.strip()
df.loc[df["country_fips"].isin(["", "nan", "None"]), "country_fips"] = pd.NA

# fips -> iso2 crosswalk (mysociety/gaze)
cw = pd.read_csv(CROSSWALK_URL)
cw.columns = ["country_fips", "country_iso2", "country_name"]

cw["country_fips"] = cw["country_fips"].astype(str).str.strip()
cw["country_iso2"] = cw["country_iso2"].astype(str).str.strip().str.upper()

# merge the crosswalk onto the gdelt rows
df = df.merge(cw, on="country_fips", how="left")

# patch missing or old fips codes
manual_patch = {
    "WA": "PS",  # west bank / palestine
    "RB": "RS",  # serbia (old code)
    "KV": "XK",  # kosovo (de-facto iso2, not official iso-3166)
}
df.loc[df["country_fips"] == "KV", "country_iso2"] = "XK"
df["country_iso2"] = df["country_iso2"].fillna(df["country_fips"].map(manual_patch))

# normalize iso2
df["country_iso2"] = df["country_iso2"].astype(str).str.strip().str.upper()
df.loc[df["country_iso2"].isin(["", "NAN", "NONE"]), "country_iso2"] = pd.NA
df.loc[~df["country_iso2"].str.fullmatch(r"[A-Z]{2}", na=False), "country_iso2"] = pd.NA

# iso2 -> un region (and country name for the mapping file)
cc = coco.CountryConverter()
supported = set(cc.valid_class)

iso = df["country_iso2"].tolist()

# country name (for the mapping file)
df["country_name"] = cc.convert(iso, src="ISO2", to="name_short", not_found=None) if "name_short" in supported else df.get("country_name", None)

# un region (key output)
if "UNregion" in supported:
    df["un_region"] = cc.convert(iso, src="ISO2", to="UNregion", not_found=None)
else:
    raise RuntimeError("Your installed country_converter does not support 'UNregion'. Run `print(cc.valid_class)` to see available outputs.")

# diagnostics
print("rows total:", len(df))
print("FIPS non-null:", df["country_fips"].notna().sum())
print("ISO2 mapped:", df["country_iso2"].notna().sum())
print("UN region mapped:", df["un_region"].notna().sum())

bad_fips = df.loc[df["country_fips"].notna() & df["country_iso2"].isna(), "country_fips"].value_counts().head(25)
if len(bad_fips) > 0:
    print("\nTop FIPS codes that did not map to ISO2:")
    print(bad_fips)

# final output: date + url + geography

URL_COLUMN = "col_57"

final = (
    df[["date", URL_COLUMN, "country_iso2", "un_region"]]
    .dropna(subset=["country_iso2", "un_region"])
)

final.columns = ["date", "url", "country", "region"]

final.to_csv(config.USAID_GEOGRAPHY, index=False)

print(f"\nWrote: {config.USAID_GEOGRAPHY}")
print(final.head())
print("Rows:", len(final))