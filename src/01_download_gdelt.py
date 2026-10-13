# downloads the gdelt 1.0 daily event zips for 2025-01-20 to 2026-01-20 (skips existing)
# reads: http://data.gdeltproject.org/events/ (network)
# writes: the daily zips and a manifest with sha-256 hashes, both in data/raw/
# quick test: python src/01_download_gdelt.py --start 2025-06-13 --end 2025-06-14
import argparse
import csv
import hashlib
import sys
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

BASE_URL = "http://data.gdeltproject.org/events/"
FULL_START = date(2025, 1, 20)
FULL_END = date(2026, 1, 20)
# these 18 days (2025-06-14 to 2025-07-01) do not exist at gdelt, so a 404 is expected.
# a 404 on any other day stops the script
EXPECTED_MISSING = {date(2025, 6, 14) + timedelta(days=i) for i in range(18)}
# the full range must give exactly this many files
EXPECTED_FILES_FULL_RANGE = 348
# 0.5 s pause between requests, up to 3 tries per file
PAUSE_S = 0.5
RETRIES = 3
TIMEOUT = (10, 180)  # connect, read (seconds)
CHUNK = 1024 * 1024  # 1 mb


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def file_name(d):
    return f"{d.strftime('%Y%m%d')}.export.CSV.zip"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download(d, out_path):
    """return 'ok' or 'missing' (http 404). raise an error after the last failed try."""
    url = BASE_URL + file_name(d)
    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    last_error = None
    for attempt in range(1, RETRIES + 1):
        time.sleep(PAUSE_S)
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT) as r:
                if r.status_code == 404:
                    return "missing"
                r.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=CHUNK):
                        if chunk:
                            f.write(chunk)
            if not zipfile.is_zipfile(tmp_path):
                raise RuntimeError("downloaded file is not a valid zip")
            tmp_path.replace(out_path)
            return "ok"
        except Exception as e:  # network error, http error other than 404, or a bad zip
            last_error = e
            print(f"  attempt {attempt}/{RETRIES} failed for {file_name(d)}: {e}")
            if tmp_path.exists():
                tmp_path.unlink()
    raise RuntimeError(f"{file_name(d)}: failed after {RETRIES} attempts: {last_error}")


def write_manifest(days):
    rows = []
    for d in days:
        p = config.GDELT_DIR / file_name(d)
        if p.exists():
            rows.append({"file_name": p.name, "size_bytes": p.stat().st_size, "sha256": sha256(p)})
    with open(config.GDELT_MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file_name", "size_bytes", "sha256"])
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=FULL_START.isoformat(), help="first day, YYYY-MM-DD")
    ap.add_argument("--end", default=FULL_END.isoformat(), help="last day, YYYY-MM-DD")
    args = ap.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if start < FULL_START or end > FULL_END or start > end:
        sys.exit(f"ERROR: range must be inside {FULL_START} .. {FULL_END}")

    config.GDELT_DIR.mkdir(parents=True, exist_ok=True)
    days = list(daterange(start, end))
    n_ok = n_skip = n_expected_missing = 0

    for d in days:
        out_path = config.GDELT_DIR / file_name(d)
        if out_path.exists():
            n_skip += 1
            continue
        status = download(d, out_path)
        if status == "ok" and d in EXPECTED_MISSING:
            sys.exit(f"ERROR: {file_name(d)} now exists at the source, but the paper's corpus does not include it. "
                     f"It was saved to {out_path}. Check the source before you continue.")
        if status == "ok":
            n_ok += 1
            print(f"  {d}: downloaded")
        elif d in EXPECTED_MISSING:
            n_expected_missing += 1
            print(f"  {d}: HTTP 404 (expected: known GDELT gap)")
        else:
            sys.exit(f"ERROR: {file_name(d)} returned HTTP 404 and is not one of the 18 known missing days.")

    n_files = write_manifest(days)
    print(f"\nDone. downloaded={n_ok} skipped(existing)={n_skip} expected-404={n_expected_missing}")
    print(f"Manifest: {config.GDELT_MANIFEST} ({n_files} files)")

    if start == FULL_START and end == FULL_END and n_files != EXPECTED_FILES_FULL_RANGE:
        sys.exit(f"ERROR: expected {EXPECTED_FILES_FULL_RANGE} files, found {n_files}.")


if __name__ == "__main__":
    main()
