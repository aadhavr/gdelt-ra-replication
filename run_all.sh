#!/usr/bin/env bash
# runs the whole pipeline. bash run_all.sh uses the shipped data, --full also downloads
# all 348 gdelt files (about 2.4 gb) and rebuilds the files in data/intermediate/
# reads: data/ and the network (gdelt, github, world bank). writes: data/raw/ and outputs/
# choose the interpreter with the shell variable python, in capitals (default: python)
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python}"

if [[ "${1:-}" == "--full" ]]; then
  echo "== 1. Download all GDELT daily files"
  "$PY" src/01_download_gdelt.py
  if [[ -f data/intermediate/usaid_closure_v1/matches_rows.csv ]]; then
    echo "== 2. SKIPPED: data/intermediate/usaid_closure_v1/matches_rows.csv exists (shipped file is used)."
    echo "      To rebuild it, move the file out and run: $PY src/02_search.py"
  else
    echo "== 2. Keyword search (USAID query)"; "$PY" src/02_search.py
  fi
  echo "== 3. Map matched rows to countries/regions"
  "$PY" src/03_map.py
  echo "== 4. Build country-level dataset"
  "$PY" src/04_build_dataset.py
  echo "== 4a. Unique-URL denominator"
  "$PY" robustness/phase3_dedup_full_corpus.py
else
  echo "== 1. Download the 26 GDELT days needed by Table B5 (2025-06-01..2025-07-14; 18 expected 404s)"
  "$PY" src/01_download_gdelt.py --start 2025-06-01 --end 2025-07-14
fi

if [[ -f data/raw/V-Dem-CY-Core-v12.csv ]]; then
  echo "== 0. Filter V-Dem";      "$PY" src/00_filter_vdem.py
fi
if [[ -f data/raw/IdealpointestimatesFP_2026FP.csv ]]; then
  echo "== 0. Filter ideal points"; "$PY" src/00_filter_idealpoint.py
fi

echo "== 4b. Rebuild 3-29-v2_oda_data.csv and compare (stops if a cell differs)"
"$PY" src/04b_merge_outcomes.py

echo "== 5. Original paper tables";  "$PY" src/05_paper_tables.py

if [[ -f data/input/vdem_filtered.csv && -f data/input/idealpoint_filtered.csv ]]; then
  echo "== 6. Control-variable checks"; "$PY" robustness/oda_controls_only.py
else
  echo "== 6. SKIPPED: robustness/oda_controls_only.py needs vdem_filtered.csv and idealpoint_filtered.csv (see README.md)."
fi

echo "== 7. Phase 3 robustness";        "$PY" robustness/phase3_robustness.py
echo "== 8. Gap sensitivity (network)"; "$PY" robustness/sensitivity_analysis.py
"$PY" robustness/followup_sensitivity.py
echo "== 9. v5 analyses (network: WDI)"; "$PY" robustness/analysis.py
"$PY" robustness/analysis2.py
"$PY" robustness/analysis3.py
echo "== 10. Final table builder";      "$PY" robustness/build_all.py
echo "Done. Outputs are in outputs/."
