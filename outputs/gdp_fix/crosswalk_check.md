# Crosswalk check: blank FIPS cell of Aland

Read-only check. No script, data file or output was changed. Counts come from the shipped files
`data/input/country-codes.csv`, `data/intermediate/usaid_closure_v1/matches_rows.csv`,
`data/intermediate/country_reaction_dataset.csv`, `data/intermediate/total_articles_unique_url.csv` and
`data/input/3-29-v2_oda_data.csv`. The raw GDELT zips are not on disk, so the zip scans were not rerun.

## The cell

`country-codes.csv` has 249 rows. The `FIPS` cell of Aland (`ISO3166-1-Alpha-3` = `ALA`, line 3 of the file)
is one non-breaking space (U+00A0), not an empty field. pandas therefore reads it as text, not as NaN.
Every script then applies `.str.strip()`, which removes U+00A0, so the crosswalk dict gets the key `""` (empty
string) mapped to `ALA`. No other row has a blank `FIPS`, and no other key maps to `ALA`. (Separately, `NL`
appears twice, for `BES` and `NLD`; the dict keeps the last row, `NLD`.)

Whether a GDELT row with a blank `ActionGeo_CountryCode` (`col_51`) hits that key depends on how the row is read:

| Path | How a blank `col_51` arrives | Lookup key | Result |
|---|---|---|---|
| Raw zips, read with `csv.reader` (`04_build_dataset.py` line 103, `phase3_dedup_full_corpus.py` line 48) | `""` | `""` | mapped to `ALA` |
| `matches_rows.csv`, read with `pd.read_csv` (`04_build_dataset.py` lines 66-76; also `fix_gdp/common.py`, the `gross_aid/` loaders and `build_all.py`) | NaN, then `astype(str)` gives `"nan"`, upper case `"NAN"` | `"NAN"` | not mapped, row dropped |

`src/03_map.py` does not use `country-codes.csv` (it downloads the mysociety/gaze crosswalk and sets blank
`col_51` to NA), and no table uses its output.

## Effect

**`ALA` in the shipped intermediate files.** Because zip rows with a blank `col_51` are counted under `ALA`:

| File | `ALA` value |
|---|---|
| `country_reaction_dataset.csv` | `total_articles` 1,093,772; `usaid_articles` 0; `days_observed` 348; `attention_share` 0; `days_to_first_article` empty |
| `total_articles_unique_url.csv` | `total_articles_unique_url` 684,479 (second largest of 236, after USA 3,243,623) |

Finland (`FIN`, FIPS `FI`) is separate: `total_articles` 52,017, `total_articles_unique_url` 15,381.
These `ALA` values are rows and URLs with no event country, not coverage of Aland.

**The 102 analysis countries: not affected.** `ALA` is not one of the 102 rows of `3-29-v2_oda_data.csv`.
Each GDELT row maps to at most one ISO3 through its own `col_51`, and the `""` key only catches rows whose
code is blank; a row with a non-blank code is looked up the same way with or without it. So no row moves
into or out of a sample country. All 102 sample countries are in `country_reaction_dataset.csv`, and their
`attention_share` in `3-29-v2_oda_data.csv` equals the value there to 6 decimals for 101 of 102 (one differs
by 0.000001; INVENTORY.md section 1.4 notes differences of this size). The analysis scripts merge
`total_articles_unique_url.csv` onto the 102 countries by `ISO3`, so the `ALA` row is never used.

**Matched USAID rows: not affected.** `matches_rows.csv` has 12,017 rows. 117 have a blank `col_51`
(71 distinct URLs). They are read as NaN and become `"NAN"`, so 0 matched rows map to `ALA`; this is why
`ALA` has `usaid_articles` 0. 11,833 rows map to a country (2,427 distinct URLs). The other 67 unmapped rows
have FIPS codes that are not in the crosswalk: `RI` 19, `WE` 14, `KV` 13, `RB` 12, `GZ` 9.
11,833 + 117 + 67 = 12,017, and 11,833 equals the sum of `usaid_articles` over all 236 rows of
`country_reaction_dataset.csv`.

**`total_articles_unique_url.csv`: affected only in the `ALA` row.** The 684,479 blank-code URLs are counted
under `ALA` and in no other row. The 102 sample values are unchanged by it.

## Not checked

The same `fips_to_iso3.get()` lookup on raw zip rows is in `robustness/sensitivity_analysis.py` (line 200),
`robustness/followup_sensitivity.py` (line 210) and `robustness/build_all.py` (line 861), so blank-code rows
there would also go to `ALA`. Those scripts need the GDELT zips and were not run or reviewed for this check.
Any analysis that uses all 236 rows of `country_reaction_dataset.csv` or `total_articles_unique_url.csv`
(rather than the 102 sample countries) would include the `ALA` row; this check did not search for such uses.
