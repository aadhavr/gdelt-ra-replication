# counts unique article urls (col 57) per country (event location, col 51), all days
# this is the denominator of the unique-url attention share
# reads: all zips in data/raw/, data/input/country-codes.csv
# writes: data/intermediate/total_articles_unique_url.csv (overwrites the shipped file)
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

import csv
import io
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

GDELT_DIR = config.GDELT_DIR
CC_PATH = config.COUNTRY_CODES
OUT_PATH = config.TOTAL_UNIQUE_URL

cc = pd.read_csv(CC_PATH, dtype=str)
cc["FIPS"] = cc["FIPS"].astype(str).str.strip().str.upper()
fips_to_iso3 = dict(zip(cc["FIPS"], cc["ISO3166-1-Alpha-3"]))


def iter_rows_from_zip(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if not names:
            return
        with zf.open(names[0], "r") as f:
            txt = io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline="")
            reader = csv.reader(txt, delimiter="\t")
            for row in reader:
                yield row


country_urls = {}  # iso3 -> set(url)
files = sorted(GDELT_DIR.glob("*.zip"))
t0 = time.time()
for i, zip_path in enumerate(files, 1):
    for row in iter_rows_from_zip(zip_path):
        if len(row) <= 57:
            continue
        fips = row[51].strip().upper()
        iso3 = fips_to_iso3.get(fips)
        if iso3 is None:
            continue
        url = row[57]
        if not url:
            continue
        country_urls.setdefault(iso3, set()).add(url)
    if i % 50 == 0 or i == len(files):
        elapsed = time.time() - t0
        print(f"  processed {i}/{len(files)} files ({elapsed:.0f}s elapsed)", flush=True)

rows = [{"ISO3": iso3, "total_articles_unique_url": len(urls)} for iso3, urls in country_urls.items()]
out_df = pd.DataFrame(rows).sort_values("ISO3")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
out_df.to_csv(OUT_PATH, index=False)
print(f"\nDone. Wrote {len(out_df)} countries to {OUT_PATH}")
print(f"Total elapsed: {time.time()-t0:.0f}s")
