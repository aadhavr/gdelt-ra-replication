# exploratory: us-specific vs general aid dependency (not in the paper)
# reproduce the us-specific vs general oda exposure comparisons
# reads: data/input/ (aid data, aid source sheet, wdi snapshot), data/intermediate/ (country reaction dataset)
# writes: us_specific_results.csv, analysis_sample.csv and log.txt in this folder
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

# import config.py from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

OUT = Path(__file__).resolve().parent

MODELS = {
    'US aid/GDP': 'usaid_articles ~ log_us_gdp',
    'Total ODA/GDP': 'usaid_articles ~ log_oda_gdp',
    'US share of ODA': 'usaid_articles ~ log_us_oda_share',
    'US aid/GDP + total ODA/GDP': 'usaid_articles ~ log_us_gdp + log_oda_gdp',
    'Total ODA/GDP + US share of ODA': 'usaid_articles ~ log_oda_gdp + log_us_oda_share',
    'US aid/GDP + absolute US aid': 'usaid_articles ~ log_us_gdp + log_us_aid',
    'US aid/GDP + total ODA/GDP + absolute US aid': 'usaid_articles ~ log_us_gdp + log_oda_gdp + log_us_aid',
}


class Tee:  # copy everything printed to log.txt
    def __init__(self, path):
        self.file = open(path, "w")
        self.stdout = sys.stdout

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def clean_number(s):
    return pd.to_numeric(s.astype(str).str.replace(',', '', regex=False).str.replace('$', '', regex=False), errors='coerce')

def main():
    sys.stdout = Tee(OUT / "log.txt")
    print("exploratory: us-specific vs general aid dependency")
    base = pd.read_csv(config.ODA_DATA)
    oda = pd.read_csv(config.ODA_SOURCE_SHEET_CSV, skiprows=3)
    wdi = pd.read_csv(config.WDI_SNAPSHOT)
    outcomes = pd.read_csv(config.COUNTRY_REACTION).rename(columns={'iso3': 'ISO3'})
    d = base.merge(oda[['ISO3', 'Avg Annual ODA Received ($M)']], on='ISO3', how='left')
    d = d.merge(wdi[['ISO3', 'population_avg', 'gdp_avg']], on='ISO3', how='left')
    d = d.merge(outcomes[['ISO3', 'total_articles', 'usaid_articles']], on='ISO3', how='left')
    d['us_aid_m'] = clean_number(d['us_oda_disbursements'])
    d['total_oda_m'] = clean_number(d['Avg Annual ODA Received ($M)'])
    d['us_gdp'] = d['us_aid_m'] * 1e6 / d['gdp_avg']
    d['oda_gdp'] = d['total_oda_m'] * 1e6 / d['gdp_avg']
    d['us_oda_share'] = d['us_aid_m'] / d['total_oda_m']
    for col, logcol in [('us_gdp', 'log_us_gdp'), ('oda_gdp', 'log_oda_gdp'),
                        ('us_oda_share', 'log_us_oda_share'), ('us_aid_m', 'log_us_aid')]:
        d[logcol] = np.log(d[col].where(d[col] > 0))
    d['log_volume'] = np.log(d['total_articles'].where(d['total_articles'] > 0))
    required = ['ISO3', 'usaid_articles', 'total_articles', 'log_volume', 'log_us_gdp',
                'log_oda_gdp', 'log_us_oda_share', 'log_us_aid']
    z = d[required].replace([np.inf, -np.inf], np.nan).dropna().copy()
    z.to_csv(OUT / 'analysis_sample.csv', index=False)
    print(f'Common sample: {len(z)} countries; matched events: {z.usaid_articles.sum():.0f}')
    print('Note: GLM NegativeBinomial alpha=1 FIXED; HC3 robust standard errors; log(total events) offset.')
    print('Log measures exclude zero/negative inputs; all models use the same complete-case sample.')
    rows = []
    for label, formula in list(MODELS.items()) + [
        ('Restricted >=5 matched EVENT ROWS: US aid/GDP + total ODA/GDP', MODELS['US aid/GDP + total ODA/GDP']),
        ('Restricted >=5 matched EVENT ROWS: US aid/GDP + absolute US aid', MODELS['US aid/GDP + absolute US aid']),
    ]:
        sample = z[z['usaid_articles'] >= 5] if label.startswith('Restricted') else z
        fit = smf.glm(formula, data=sample, family=sm.families.NegativeBinomial(alpha=1),
                      offset=sample['log_volume']).fit(cov_type='HC3')
        for variable in fit.params.index:
            if variable == 'Intercept':
                continue
            lo, hi = fit.conf_int().loc[variable]
            rows.append({'model': label, 'n': int(fit.nobs), 'variable': variable,
                         'beta': fit.params[variable], 'se': fit.bse[variable],
                         'p': fit.pvalues[variable], 'ci_low': lo, 'ci_high': hi, 'aic': fit.aic})
        print(f'{label}: N={int(fit.nobs)}; ' + ', '.join(
            f'{v}={fit.params[v]:.3f} (p={fit.pvalues[v]:.4g})' for v in fit.params.index if v != 'Intercept'))
    pd.DataFrame(rows).to_csv(OUT / 'us_specific_results.csv', index=False)
    print(f"files written to {OUT.relative_to(config.ROOT)}/")

if __name__ == '__main__':
    main()
