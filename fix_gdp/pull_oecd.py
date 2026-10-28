# gdp fix step 2b: one sdmx call for oecd dac2a gross oda (measure 240, usd), donors usa and dac total,
#   price bases q (constant 2024) and v (current), all recipients, 2018-2022. no retries
# reads: sdmx.oecd.org
# writes: data/raw_oecd_pull/dac2a_usa_dac_240_QV_2018_2022.csv (raw response, as received) and
#   data/raw_oecd_pull/dac2a_usa_dac_240_QV_2018_2022.query.txt (url, time, status); stops if either exists
import sys
from datetime import datetime, timezone

import requests

from common import ROOT

PULL = ROOT / "data" / "raw_oecd_pull"
NAME = "dac2a_usa_dac_240_QV_2018_2022"
# key: DONOR.RECIPIENT.MEASURE.UNIT_MEASURE.PRICE_BASE (recipient empty = all)
URL = ("https://sdmx.oecd.org/public/rest/data/OECD.DCD.FSD,DSD_DAC2@DF_DAC2A,1.7/USA+DAC..240.USD.Q+V"
       "?startPeriod=2018&endPeriod=2022&dimensionAtObservation=AllDimensions&format=csvfilewithlabels")


def main():
    data, meta = PULL / f"{NAME}.csv", PULL / f"{NAME}.query.txt"
    for p in (data, meta):
        if p.exists():
            sys.exit(f"STOP: {p.relative_to(ROOT)} exists, not overwriting.")
    PULL.mkdir(exist_ok=True)
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    r = requests.get(URL, timeout=(10, 120))
    meta.write_text(f"url: {URL}\nrequested_utc: {when}\nhttp_status: {r.status_code}\n"
                    f"content_type: {r.headers.get('content-type')}\nbytes: {len(r.content)}\n")
    print(f"http {r.status_code}, {len(r.content)} bytes")
    if r.status_code != 200:
        print(r.text[:500])
        sys.exit("STOP: oecd call failed, not retrying.")
    data.write_bytes(r.content)
    print(f"wrote {data.relative_to(ROOT)} and {meta.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
