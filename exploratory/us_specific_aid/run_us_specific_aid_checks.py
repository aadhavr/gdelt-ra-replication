# exploratory: follow-up checks on run_us_specific_aid.py (not in the paper)
# (1) the same models with unique-url counts instead of matched event rows
# (2) correlation between log us aid/gdp and log total oda/gdp, vif, and a joint wald test
# (3) how negative net aid values (egypt, gabon) enter the ratios, with a bottom-coding sensitivity
# reads: data/input/ (aid data, aid source sheet, wdi snapshot, country codes),
#   data/intermediate/ (country reaction dataset, matched rows, unique url totals)
# writes: checks_results.csv, checks_collinearity.csv, checks_negative_aid.csv and checks_log.txt in this folder
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
LOG_VARS = ['log_us_gdp', 'log_oda_gdp', 'log_us_oda_share', 'log_us_aid']

# same models as run_us_specific_aid.py; the outcome name is filled in per count type
MODELS = {
    'US aid/GDP': '{y} ~ log_us_gdp',
    'Total ODA/GDP': '{y} ~ log_oda_gdp',
    'US share of ODA': '{y} ~ log_us_oda_share',
    'US aid/GDP + total ODA/GDP': '{y} ~ log_us_gdp + log_oda_gdp',
    'Total ODA/GDP + US share of ODA': '{y} ~ log_oda_gdp + log_us_oda_share',
    'US aid/GDP + absolute US aid': '{y} ~ log_us_gdp + log_us_aid',
    'US aid/GDP + total ODA/GDP + absolute US aid': '{y} ~ log_us_gdp + log_oda_gdp + log_us_aid',
}
RESTRICTED = ['US aid/GDP + total ODA/GDP', 'US aid/GDP + absolute US aid']

# outcome, offset column, label of the >=5 restriction
COUNT_TYPES = {
    'event rows': ('usaid_articles', 'log_volume', '>=5 matched EVENT ROWS'),
    'unique urls': ('usaid_articles_unique', 'log_volume_unique', '>=5 matched UNIQUE URLS'),
}


class Tee:  # copy everything printed to checks_log.txt
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


def add_ratios(d):
    # same construction as run_us_specific_aid.py
    d['us_gdp'] = d['us_aid_m'] * 1e6 / d['gdp_avg']
    d['oda_gdp'] = d['total_oda_m'] * 1e6 / d['gdp_avg']
    d['us_oda_share'] = d['us_aid_m'] / d['total_oda_m']
    for col, logcol in [('us_gdp', 'log_us_gdp'), ('oda_gdp', 'log_oda_gdp'),
                        ('us_oda_share', 'log_us_oda_share'), ('us_aid_m', 'log_us_aid')]:
        d[logcol] = np.log(d[col].where(d[col] > 0))
    return d


def nb_fit(formula, sample, offset):
    return smf.glm(formula, data=sample, family=sm.families.NegativeBinomial(alpha=1),
                   offset=sample[offset]).fit(cov_type='HC3')


def main():
    sys.stdout = Tee(OUT / "checks_log.txt")
    print("exploratory: us-specific aid dependency, follow-up checks")

    # data, lines copied from run_us_specific_aid.py
    base = pd.read_csv(config.ODA_DATA)
    oda = pd.read_csv(config.ODA_SOURCE_SHEET_CSV, skiprows=3)
    wdi = pd.read_csv(config.WDI_SNAPSHOT)
    outcomes = pd.read_csv(config.COUNTRY_REACTION).rename(columns={'iso3': 'ISO3'})
    d = base.merge(oda[['ISO3', 'Avg Annual ODA Received ($M)', 'US Avg Annual ODA Loans ($M)']], on='ISO3', how='left')
    d = d.merge(wdi[['ISO3', 'population_avg', 'gdp_avg']], on='ISO3', how='left')
    d = d.merge(outcomes[['ISO3', 'total_articles', 'usaid_articles']], on='ISO3', how='left')
    d['us_aid_m'] = clean_number(d['us_oda_disbursements'])
    d['total_oda_m'] = clean_number(d['Avg Annual ODA Received ($M)'])
    d['us_loans_m'] = clean_number(d['US Avg Annual ODA Loans ($M)'])
    d['log_volume'] = np.log(d['total_articles'].where(d['total_articles'] > 0))

    # unique-url counts, lines copied from build_all.py
    cc_raw = pd.read_csv(config.COUNTRY_CODES, dtype=str)
    cc_raw["FIPS"] = cc_raw["FIPS"].astype(str).str.strip().str.upper()
    fips_to_iso3 = dict(zip(cc_raw["FIPS"], cc_raw["ISO3166-1-Alpha-3"]))
    m = pd.read_csv(config.MATCHES_ROWS, dtype=str, low_memory=False)
    m["iso3"] = m["col_51"].astype(str).str.strip().str.upper().map(fips_to_iso3)
    m = m.dropna(subset=["iso3"])
    usaid_unique = m.groupby("iso3")["col_57"].nunique().reset_index().rename(
        columns={"iso3": "ISO3", "col_57": "usaid_articles_unique"})
    usaid_rows = m.groupby("iso3").size().reset_index(name="usaid_rows_check").rename(columns={"iso3": "ISO3"})
    d = d.merge(usaid_unique, on="ISO3", how="left").merge(usaid_rows, on="ISO3", how="left")
    d["usaid_articles_unique"] = d["usaid_articles_unique"].fillna(0)
    d["usaid_rows_check"] = d["usaid_rows_check"].fillna(0)
    d = d.merge(pd.read_csv(config.TOTAL_UNIQUE_URL), on="ISO3", how="left")
    d["log_volume_unique"] = np.log(d["total_articles_unique_url"].where(d["total_articles_unique_url"] > 0))
    n_diff = (d["usaid_rows_check"] != d["usaid_articles"]).sum()
    print(f"aid file: N = {len(d)}; countries where matched rows from matches_rows.csv != usaid_articles "
          f"in country_reaction_dataset.csv: {n_diff}")

    d = add_ratios(d)

    # (3) negative net aid: what happens to these rows
    print("\n(3) NONPOSITIVE OR MISSING INPUTS")
    print("source sheet: OECD DAC2A measure 206, net ODA disbursements (2018-2022 average). net = gross minus repayments,")
    print("so it can be negative. np.log of a nonpositive ratio is set to missing, so the country leaves the sample.")
    drop = d[(d['us_aid_m'] <= 0) | (d['total_oda_m'] <= 0) | d[['us_aid_m', 'total_oda_m', 'gdp_avg']].isna().any(axis=1)]
    neg = drop[['ISO3', 'us_aid_m', 'us_loans_m', 'total_oda_m', 'gdp_avg', 'us_gdp', 'oda_gdp', 'us_oda_share',
                'usaid_articles', 'usaid_articles_unique']].copy()
    neg['reason'] = np.where(drop['gdp_avg'].isna(), 'no gdp_avg in wdi snapshot',
                             np.where(drop['us_aid_m'] <= 0, 'net US aid <= 0', 'other'))
    print(neg.to_string(index=False))
    neg.to_csv(OUT / 'checks_negative_aid.csv', index=False)
    print(f"total ODA <= 0 in the aid file: {(d['total_oda_m'] <= 0).sum()} countries")
    print("negative US aid makes us_gdp and us_oda_share negative (and log_us_aid undefined); total ODA is positive,")
    print("so log_oda_gdp is defined for these countries, but the common complete-case sample drops them from every model.")

    # bottom-coding sensitivity: nonpositive us aid set to the smallest positive value in the sample
    floor = d.loc[(d['us_aid_m'] > 0) & d['gdp_avg'].notna() & d['total_oda_m'].notna(), 'us_aid_m'].min()
    d_bc = d.copy()
    d_bc['us_aid_m'] = d_bc['us_aid_m'].where(d_bc['us_aid_m'] > 0, floor)
    d_bc = add_ratios(d_bc)
    print(f"sensitivity: nonpositive US aid bottom-coded at the smallest positive value, {floor} (USD millions)")

    rows, coll = [], []
    for ctype, (y, offset, rlabel) in COUNT_TYPES.items():
        for dname, data in [('as published (drop nonpositive)', d), ('bottom-coded US aid', d_bc)]:
            required = ['ISO3', y, offset] + LOG_VARS
            z = data[required].replace([np.inf, -np.inf], np.nan).dropna().copy()
            print(f"\n=== {ctype} | {dname}: common sample {len(z)} countries; matched {ctype}: {z[y].sum():.0f}")
            print('GLM NegativeBinomial alpha=1 FIXED; HC3 robust standard errors; log(total ' + ctype + ') offset.')
            specs = [(k, v, z) for k, v in MODELS.items()]
            specs += [(f'Restricted {rlabel}: {k}', MODELS[k], z[z[y] >= 5]) for k in RESTRICTED]
            for label, formula, sample in specs:
                fit = nb_fit(formula.format(y=y), sample, offset)
                for variable in fit.params.index:
                    if variable == 'Intercept':
                        continue
                    lo, hi = fit.conf_int().loc[variable]
                    rows.append({'count_type': ctype, 'aid_values': dname, 'model': label, 'n': int(fit.nobs),
                                 'variable': variable, 'beta': fit.params[variable], 'se': fit.bse[variable],
                                 'p': fit.pvalues[variable], 'ci_low': lo, 'ci_high': hi, 'aic': fit.aic})
                print(f'{label}: N={int(fit.nobs)}; ' + ', '.join(
                    f'{v}={fit.params[v]:.3f} (p={fit.pvalues[v]:.4g})' for v in fit.params.index if v != 'Intercept'))

            # (2) collinearity and joint test, full and restricted samples
            for sname, sample in [('full', z), (f'restricted {rlabel}', z[z[y] >= 5])]:
                r = sample['log_us_gdp'].corr(sample['log_oda_gdp'])
                rho = sample['log_us_gdp'].corr(sample['log_oda_gdp'], method='spearman')
                fit = nb_fit(MODELS['US aid/GDP + total ODA/GDP'].format(y=y), sample, offset)
                w = fit.wald_test('log_us_gdp = 0, log_oda_gdp = 0', scalar=True)
                coll.append({'count_type': ctype, 'aid_values': dname, 'sample': sname, 'n': len(sample),
                             'pearson_r': r, 'spearman_rho': rho, 'vif': 1 / (1 - r ** 2),
                             'joint_wald_chi2': float(w.statistic), 'joint_wald_df': 2,
                             'joint_wald_p': float(w.pvalue)})
                print(f"  collinearity, {sname} (N={len(sample)}): r(log US aid/GDP, log total ODA/GDP) = {r:.3f}, "
                      f"spearman = {rho:.3f}, VIF = {1 / (1 - r ** 2):.2f}; joint HC3 Wald test both = 0: "
                      f"chi2(2) = {float(w.statistic):.2f}, p = {float(w.pvalue):.3g}")

    # full correlation matrix of the four regressors, published sample
    z = d[['usaid_articles', 'log_volume'] + LOG_VARS].replace([np.inf, -np.inf], np.nan).dropna()
    print(f"\ncorrelation matrix of the log regressors (published sample, N = {len(z)}):")
    print(z[LOG_VARS].corr().round(3).to_string())
    resid = (z['log_us_gdp'] - z['log_oda_gdp'] - z['log_us_oda_share']).abs().max()
    print(f"identity check: max |log_us_gdp - log_oda_gdp - log_us_oda_share| = {resid:.2e} "
          "(so the 'US aid/GDP + total ODA/GDP' and 'total ODA/GDP + US share' models are the same model)")

    pd.DataFrame(rows).to_csv(OUT / 'checks_results.csv', index=False)
    pd.DataFrame(coll).to_csv(OUT / 'checks_collinearity.csv', index=False)
    print(f"files written to {OUT.relative_to(config.ROOT)}/")


if __name__ == '__main__':
    main()
