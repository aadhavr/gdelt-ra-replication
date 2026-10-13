# rebuilds data/input/3-29-v2_oda_data.csv from the aid sheet and checks it cell by cell
# against the shipped copy. no script in the original project made this file
# reads: data/input/3_29__oda_data.csv (and data/input/3-29-v2_oda_data.csv for the check)
# writes: outputs/04b_merge_outcomes/3-29-v2_oda_data.csv, exit code 1 if any cell differs
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

TITLE_ROWS = 3  # title rows above the header row
MATCHED_COL = "GDELT Matched"
MATCHED_VALUE = "✓"  # the 102 countries in the gdelt data
# (sheet column, output column). cells stay text, so "2,128.8" and "n/a" do not change
COLUMN_MAP = [
    ("ISO3", "ISO3"),
    ("Country", "country"),
    ("US Avg Annual ODA Disbursements ($M)", "us_oda_disbursements"),
    ("US Avg Annual ODA Loans ($M)", "us_oda_loans"),
    ("Attention Share", "attention_share"),
    ("Days to 1st Article", "days_to_first_article"),
]
OUT_DIR = config.OUTPUTS_DIR / "04b_merge_outcomes"
OUT_PATH = OUT_DIR / "3-29-v2_oda_data.csv"


def read_rows(path, skip=0):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return rows[skip:]


def main():
    sheet = read_rows(config.ODA_SOURCE_SHEET_CSV, skip=TITLE_ROWS)
    header, body = sheet[0], sheet[1:]
    idx = {name: header.index(name) for name, _ in COLUMN_MAP + [(MATCHED_COL, None)]}

    out_rows = [[new for _, new in COLUMN_MAP]]
    for r in body:
        if r[idx[MATCHED_COL]] == MATCHED_VALUE:
            out_rows.append([r[idx[old]] for old, _ in COLUMN_MAP])

    buf = io.StringIO()
    csv.writer(buf).writerows(out_rows)  # csv writes crlf line ends by default
    text = buf.getvalue()
    if text.endswith("\r\n"):
        text = text[:-2]  # shipped file has no newline at the end
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        f.write(text)

    # compare with the shipped file, cell by cell
    shipped = read_rows(config.ODA_DATA)
    n_cells = n_diff = 0
    if len(shipped) != len(out_rows):
        print(f"Row count differs: rebuilt {len(out_rows)}, shipped {len(shipped)}")
        n_diff += 1
    for i, (a, b) in enumerate(zip(out_rows, shipped)):
        if len(a) != len(b):
            print(f"Row {i}: column count differs ({len(a)} vs {len(b)})")
            n_diff += 1
            continue
        for j, (x, y) in enumerate(zip(a, b)):
            n_cells += 1
            if x != y:
                n_diff += 1
                print(f"Row {i} ({a[0]}), column {out_rows[0][j]}: rebuilt {x!r}, shipped {y!r}")
    same_bytes = OUT_PATH.read_bytes() == config.ODA_DATA.read_bytes()
    print(f"Rebuilt {len(out_rows) - 1} rows -> {OUT_PATH}")
    print(f"Cells compared: {n_cells} | differing: {n_diff} | byte-identical file: {same_bytes}")
    sys.exit(0 if n_diff == 0 else 1)


if __name__ == "__main__":
    main()
