# keeps the gdelt rows with a usaid marker (bucket a) and a disruption word (bucket b)
# reads: the daily zips in data/raw/, 2025-01-20 to 2026-01-20
# writes: data/intermediate/usaid_closure_v1/matches_rows.csv (stops if it exists)
# the main block at the end runs the usaid query
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional


# query definition

@dataclass(frozen=True)
class QuerySpec:
    name: str
    # include_any: bucket a in two_bucket_and mode (at least one must match)
    include_any: List[str]
    # include_all: bucket b (at least one must match, not all, despite the name)
    include_all: List[str] = None
    # exclude_any: drop the row if any of these match
    exclude_any: List[str] = None
    # mode "any": keep the row if any include_any word matches
    # mode "two_bucket_and": needs one word from bucket a and one from bucket b
    mode: str = "ANY"


USAID_CLOSURE = QuerySpec(
    name="usaid_closure_v1",
    # bucket a: at least one usaid marker
    include_any=["USAID", "USAGOVDEV"],

    # bucket b: at least one shutdown / freeze word
    include_all=[
        "freeze", "funding freeze", "aid freeze",
        "pause", "aid pause", "funding pause",
        "cut", "aid cut", "funding cut",
        "shutdown", "closure", "halt", "suspend", "suspension", "defund",
    ],

    exclude_any=[],
    mode="TWO_BUCKET_AND",
)

# a second query, not used by this project
CHINA_DEV_GLOBAL = QuerySpec(
    name="china_dev_global_v1",
    include_any=[
        "Belt and Road", "Belt & Road", "Belt Road",
        "Belt and Road Initiative", "Belt & Road Initiative", "Belt Road Initiative",
        "Global Development Initiative", "Global Dev Initiative",
    ],

    include_all=[
    ],

    exclude_any=[
        "brianna", "BRITISH", "Britain", "Briton",
        "gdi.exe", "gdi32", "graphics device interface"
    ],

    mode="TWO_BUCKET_AND"
)

EVENTS_DIR = config.GDELT_DIR
OUTPUTS_DIR = config.SEARCH_OUTPUT_DIR
START_DATE = datetime(2025, 1, 20) 
END_DATE = datetime(2026, 1, 20)  # not used: timeout (10, 180), dl_chunk 1 mb

# helpers

def daterange(start: datetime, end: datetime) -> Iterable[datetime]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def day_filename(day: datetime) -> str:
    return f"{day.strftime('%Y%m%d')}.export.CSV.zip"

def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def row_matches(text: str, spec: QuerySpec) -> bool:
    t = text.lower()

    if spec.exclude_any:
        for kw in spec.exclude_any:
            if kw and kw.lower() in t:
                return False

    if spec.mode == "ANY":
        return any(kw.lower() in t for kw in spec.include_any if kw)

    if spec.mode == "TWO_BUCKET_AND":
        # bucket a and bucket b must each match at least once
        hit_a = any(kw.lower() in t for kw in spec.include_any if kw)
        hit_b = any(kw.lower() in t for kw in (spec.include_all or []) if kw)
        return hit_a and hit_b

    raise ValueError(f"Unknown mode: {spec.mode}")


def iter_rows_from_zip(zip_path: Path) -> Iterable[List[str]]:
    """
    yields rows from the single inner file in a daily gdelt export zip.
    the export is tab-delimited and has no header row.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        # the first file in the zip is the export
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if not names:
            return
        inner = names[0]
        with zf.open(inner, "r") as f:
            # read the bytes as text
            txt = io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline="")
            reader = csv.reader(txt, delimiter="\t")
            for row in reader:
                yield row


def append_matches_to_one_csv(
    zip_path: Path,
    day: datetime,
    spec: QuerySpec,
    out_csv: Path,
) -> int:
    """
    scans all rows (all columns) for keyword matches and appends them to one output csv.
    adds a leading 'date' column (yyyymmdd) to each written row.
    returns the number of rows written.
    """
    safe_mkdir(out_csv.parent)

    # append mode: one csv for all days
    wrote = 0
    date_str = day.strftime("%Y%m%d")

    # write the header only when the file is new
    file_exists = out_csv.exists()
    with open(out_csv, "a", newline="", encoding="utf-8") as out_f:
        writer = csv.writer(out_f)

        if not file_exists:
            # count the columns from the first row of the zip
            first_row = next(iter_rows_from_zip(zip_path), None)
            if first_row is None:
                return 0
            header = ["date"] + [f"col_{i}" for i in range(len(first_row))]
            writer.writerow(header)

            # the first row is checked here and again in the loop below
            # (known issues file, section b2)
            blob = " | ".join(first_row)
            if row_matches(blob, spec):
                writer.writerow([date_str] + first_row)
                wrote += 1

        for row in iter_rows_from_zip(zip_path):
            # search all columns, including the url
            blob = " | ".join(row)
            if row_matches(blob, spec):
                writer.writerow([date_str] + row)
                wrote += 1

    return wrote


# main

def run_query(spec: QuerySpec) -> None:
    EVENTS_DIR.mkdir(exist_ok=True)
    out_dir = OUTPUTS_DIR / spec.name
    safe_mkdir(out_dir)

    out_csv = out_dir / "matches_rows.csv"
    if out_csv.exists():
        raise SystemExit(
            f"ERROR: output file already exists: {out_csv}\n"
            "This script appends rows, so a second run would duplicate them. "
            "Move or delete the file first, then run again."
        )

    total_written = 0
    for day in daterange(START_DATE, END_DATE):
        zip_path = EVENTS_DIR / day_filename(day)
        if not zip_path.exists():
            continue
        if not zipfile.is_zipfile(zip_path):
            print(f"Skipping invalid zip: {zip_path.name}")
            continue

        wrote = append_matches_to_one_csv(zip_path, day, spec, out_csv)
        total_written += wrote

        print(f"  {day.strftime('%Y-%m-%d')}: wrote {wrote} matching rows")

    print("\nDone.")
    print(f"Query: {spec.name}")
    print(f"Output: {out_csv}")
    print(f"Total matching rows appended: {total_written}")


if __name__ == "__main__":
    # run the usaid query
    run_query(USAID_CLOSURE)