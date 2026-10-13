# builds the country dataset: gdelt rows and matched rows per country (event location),
# attention share (matched / all rows) and days from 2025-01-20 to the first match
# reads: matched rows in data/intermediate/, data/raw/ zips, data/input/country-codes.csv
# writes: data/intermediate/country_reaction_dataset.csv (overwrites the shipped file)
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

import pandas as pd
import numpy as np
from pathlib import Path
import zipfile
import io
import csv

# settings
USAID_PATH = config.MATCHES_ROWS
GDELT_DIR = config.GDELT_DIR
CROSSWALK_PATH = config.COUNTRY_CODES
OUTPUT_PATH = config.COUNTRY_REACTION
EVENT_DATE = "2025-01-20"

# fips → iso3 crosswalk
fips_df = pd.read_csv(CROSSWALK_PATH)

# normalize column names
fips_df.columns = [c.strip().lower() for c in fips_df.columns]

# normalize values
fips_df['fips'] = fips_df['fips'].astype(str).str.strip().str.upper()

# detect iso3 column (robust)
iso3_col = None
for col in fips_df.columns:
    if 'iso3' in col or 'alpha-3' in col or 'alpha3' in col:
        iso3_col = col
        break

if iso3_col is None:
    raise ValueError(f"Could not find ISO3 column. Columns: {fips_df.columns.tolist()}")

fips_df[iso3_col] = fips_df[iso3_col].astype(str).str.strip().str.upper()

# build mapping
fips_to_iso3 = dict(zip(fips_df['fips'], fips_df[iso3_col]))

print("Loaded FIPS→ISO3 mapping. Sample:")
print(list(fips_to_iso3.items())[:10])
# read a gdelt zip
def iter_rows_from_zip(zip_path: Path):
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if not names:
            return
        inner = names[0]
        with zf.open(inner, "r") as f:
            txt = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
            reader = csv.reader(txt, delimiter="\t")
            for row in reader:
                yield row

# load the matched rows
print("Loading USAID filtered data...")
usaid_df = pd.read_csv(USAID_PATH)

usaid_df['date'] = pd.to_datetime(usaid_df['date'], format='%Y%m%d')

usaid_df['iso3'] = (
    usaid_df['col_51']
    .astype(str)
    .str.strip()
    .str.upper()
    .map(fips_to_iso3)
)
usaid_df = usaid_df.dropna(subset=['iso3'])

# matched rows per country and day
print("Aggregating USAID daily counts...")
usaid_daily = (
    usaid_df.groupby(['iso3', 'date'])
    .size()
    .reset_index(name='usaid_articles')
)

# all gdelt rows per country and day (scans every zip)
print("Computing total daily counts from raw GDELT...")

rows = []

for zip_path in sorted(GDELT_DIR.glob("*.zip")):
    date_str = zip_path.name[:8]
    date = pd.to_datetime(date_str, format='%Y%m%d')

    counts = {}

    try:
        for row in iter_rows_from_zip(zip_path):
            if len(row) <= 51:
                continue

            fips = row[51].strip().upper()
            iso3 = fips_to_iso3.get(fips)

            if iso3 is None:
                continue

            counts[iso3] = counts.get(iso3, 0) + 1

    except Exception as e:
        print(f"Skipping {zip_path.name}: {e}")
        continue

    for iso3, count in counts.items():
        rows.append((iso3, date, count))

    print(f"Processed {zip_path.name}")

total_daily = pd.DataFrame(rows, columns=['iso3', 'date', 'total_articles'])

# merge the daily counts
print("Merging datasets...")

daily = total_daily.merge(
    usaid_daily,
    on=['iso3', 'date'],
    how='left'
)

daily['usaid_articles'] = daily['usaid_articles'].fillna(0)

# country totals
print("Aggregating to country level...")

country_df = (
    daily.groupby('iso3')
    .agg(
        total_articles=('total_articles', 'sum'),
        usaid_articles=('usaid_articles', 'sum'),
        days_observed=('date', 'nunique')
    )
    .reset_index()
)

country_df['total_articles_per_day'] = (
    country_df['total_articles'] / country_df['days_observed']
)

country_df['usaid_articles_per_day'] = (
    country_df['usaid_articles'] / country_df['days_observed']
)

country_df['attention_share'] = (
    country_df['usaid_articles'] / country_df['total_articles']
)

country_df['attention_share'] = country_df['attention_share'].replace(
    [np.inf, -np.inf], np.nan
)

# days to first article
print("Computing days to first article...")

event_date = pd.to_datetime(EVENT_DATE)

first_mentions = (
    usaid_daily[usaid_daily['usaid_articles'] > 0]
    .groupby('iso3')['date']
    .min()
    .reset_index()
)

first_mentions['days_to_first_article'] = (
    first_mentions['date'] - event_date
).dt.days

country_df = country_df.merge(
    first_mentions[['iso3', 'days_to_first_article']],
    on='iso3',
    how='left'
)

# output
print("Saving final dataset...")

country_df.to_csv(OUTPUT_PATH, index=False)

print("\nDone.")
print(country_df.head())