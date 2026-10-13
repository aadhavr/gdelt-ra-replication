#!/usr/bin/env python3
# keeps the 5 columns we use from the v-dem country-year core v12 file
# reads: the v-dem csv in data/raw/ (download it yourself, see the readme)
# writes: data/input/vdem_filtered.csv
"""filter the v-dem csv to a smaller set of columns."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config


COLUMNS = [
    "country_name",
    "country_text_id",
    "year",
    "v2mecenefm",
    "v2meharjrn",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Keep only a selected set of columns from the V-Dem CSV file."
    )
    parser.add_argument(
        "input_csv",
        nargs="?",
        default=str(config.VDEM_RAW),
        help="Path to the input V-Dem CSV file.",
    )
    parser.add_argument(
        "output_csv",
        nargs="?",
        default=str(config.VDEM_FILTERED),
        help="Path for the filtered output CSV file.",
    )
    return parser.parse_args()


def filter_columns(input_path: Path, output_path: Path) -> None:
    with input_path.open("r", newline="", encoding="utf-8", errors="replace") as src:
        reader = csv.DictReader(src)
        missing = [col for col in COLUMNS if col not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"Input CSV is missing required columns: {', '.join(missing)}"
            )

        with output_path.open("w", newline="", encoding="utf-8") as dst:
            writer = csv.DictWriter(dst, fieldnames=COLUMNS)
            writer.writeheader()
            for row in reader:
                writer.writerow({col: row[col] for col in COLUMNS})


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    filter_columns(input_path, output_path)
    print(f"Filtered CSV saved to: {output_path}")


if __name__ == "__main__":
    main()
