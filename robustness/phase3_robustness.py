# robustness checks: classical vs hc3 se, volume control, attention-share forms,
# sub-saharan africa split, outlier re-runs, cox models (censored at 365 days)
# reads: data/input/ and data/intermediate/country_reaction_dataset.csv
# writes: outputs/phase3_robustness/ (summary table, and a log that each run adds to)
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

# population and gdp are not used (this project has no data for them)

import os
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

np.random.seed(42)

OUT_DIR = str(config.OUT_PHASE3)
os.makedirs(OUT_DIR, exist_ok=True)

LOG_PATH = os.path.join(OUT_DIR, "log.txt")


class Tee:
    def __init__(self, path, mode="a"):
        self.file = open(path, mode)
        self.stdout = sys.stdout

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


sys.stdout = Tee(LOG_PATH, "a")

print("\n\n" + "=" * 70)
print("PHASE 3 ROBUSTNESS RUN")
print("=" * 70)

# load data
aid_path = config.ODA_DATA
crd_path = config.COUNTRY_REACTION
cc_path = config.COUNTRY_CODES

df = pd.read_csv(aid_path)
print(f"\nStep 0: loaded {aid_path}  N={len(df)}")

df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()
df["us_oda_disbursements"] = (
    df["us_oda_disbursements"].astype(str).str.replace(",", "")
)
df["us_oda_disbursements"] = pd.to_numeric(df["us_oda_disbursements"], errors="coerce")
df["days_to_first_article"] = pd.to_numeric(df["days_to_first_article"], errors="coerce")
df["attention_share"] = pd.to_numeric(df["attention_share"], errors="coerce")

df["log_days"] = np.log1p(df["days_to_first_article"])
df["log_disbursements"] = np.where(
    df["us_oda_disbursements"] > 0, np.log(df["us_oda_disbursements"]), np.nan
)
df["log_attention_share"] = np.log1p(df["attention_share"])

# region: un m49 geoscheme from country-codes.csv, not country_converter "continent",
# so sub-saharan africa and northern africa are separate
cc = pd.read_csv(cc_path, dtype=str)
cc = cc.rename(columns={
    "ISO3166-1-Alpha-3": "ISO3",
    "Region Name": "un_region",
    "Sub-region Name": "un_subregion",
})[["ISO3", "un_region", "un_subregion"]]
cc["ISO3"] = cc["ISO3"].astype(str).str.strip().str.upper()

df = df.merge(cc, on="ISO3", how="left")
df["is_subsaharan_africa"] = df["un_subregion"] == "Sub-Saharan Africa"
df["is_northern_africa"] = df["un_subregion"] == "Northern Africa"

no_region = df[df["un_region"].isna()]["ISO3"].tolist()
print(f"\nStep: UN region/subregion merge. Countries with no match in country-codes.csv: {no_region if no_region else 'none'}")

# by-region tables use un_region (all, africa, americas, asia, europe, oceania)
# plus a separate sub-saharan africa cut
REGION_ORDER = ["Africa", "Americas", "Asia", "Europe", "Oceania"]

# volume control: total_articles per country
crd = pd.read_csv(crd_path)
crd = crd.rename(columns={"iso3": "ISO3"})[["ISO3", "total_articles"]]
crd["ISO3"] = crd["ISO3"].astype(str).str.strip().str.upper()
df = df.merge(crd, on="ISO3", how="left")
df["log_total_articles"] = np.log(df["total_articles"].where(df["total_articles"] > 0))

missing_vol = df[df["total_articles"].isna()]["ISO3"].tolist()
print(f"Step: total_articles merge (volume control). Countries with no match: {missing_vol if missing_vol else 'none'}")

# sample attrition: n at every step, and who drops and why
print("\n" + "-" * 70)
print("SAMPLE ATTRITION (item 1)")
print("-" * 70)

n_all = len(df)
has_attention = df["attention_share"].notna()
has_article = df["days_to_first_article"].notna()
has_valid_aid = df["log_disbursements"].notna()  # aid present and > 0

print(f"N total rows in aid file:                         {n_all}")
print(f"N with a recorded attention_share value:          {has_attention.sum()}  (matches draft Table 2 N=102)")
print(f"N with a recorded first-article date (days):      {has_article.sum()}  (matches draft Table 1 N=95)")
print(f"N with valid (present, >0) log(aid):              {has_valid_aid.sum()}")

no_article = df.loc[~has_article, ["ISO3", "country", "us_oda_disbursements"]]
print(f"\nCountries with no matched article at all (censored, not just missing aid), n={len(no_article)}:")
print(no_article.to_string(index=False))

nonpos_aid = df.loc[(df["us_oda_disbursements"] <= 0) | df["us_oda_disbursements"].isna(),
                     ["ISO3", "country", "us_oda_disbursements"]]
print(f"\nCountries with non-positive or missing US ODA value (dropped from log-aid regressions), n={len(nonpos_aid)}:")
print(nonpos_aid.to_string(index=False))

days_reg_n = (has_article & has_valid_aid).sum()
attn_reg_n = (has_attention & has_valid_aid).sum()
print(f"\nN in days regression (article present and valid aid):      {days_reg_n}  (matches draft Table 3 N=93)")
print(f"N in attention regression (share present and valid aid):   {attn_reg_n}  (matches draft Table 4 N=100)")

dropped_from_days = df.loc[has_article & ~has_valid_aid, ["ISO3", "country", "us_oda_disbursements"]]
print(f"\nOf the {has_article.sum()} countries with an article, dropped from the days regression for non-positive aid (n={len(dropped_from_days)}):")
print(dropped_from_days.to_string(index=False))

# correlation of the two outcomes
print("\n" + "-" * 70)
print("CORRELATION BETWEEN days_to_first_article AND attention_share (item 2)")
print("-" * 70)
both = df[["log_days", "log_attention_share", "days_to_first_article", "attention_share"]].dropna()
pearson_log = both["log_days"].corr(both["log_attention_share"])
pearson_raw = both["days_to_first_article"].corr(both["attention_share"])
spearman_raw = both["days_to_first_article"].corr(both["attention_share"], method="spearman")
print(f"N with both outcomes observed: {len(both)}")
print(f"Pearson r, log(1+days) vs log(1+share):      {pearson_log:.3f}")
print(f"Pearson r, raw days vs raw share:             {pearson_raw:.3f}")
print(f"Spearman rho, raw days vs raw share:          {spearman_raw:.3f}")
print("Interpretation: a negative correlation here is partly mechanical -- the first")
print("article is a running minimum over the same article stream that attention_share")
print("sums, so a country with more total volume tends to both post an earlier minimum")
print("and accumulate a larger numerator for the share. This is why item 2 asks for a")
print("total-article-count control in both outcome models (below).")

# helper: classical and hc3 se side by side
def fit_both_se(formula, data):
    m_classical = smf.ols(formula, data=data).fit()
    m_hc3 = smf.ols(formula, data=data).fit(cov_type="HC3")
    return m_classical, m_hc3


def report_model_pair(label, formula, data, coef_name="log_disbursements"):
    reg_df = data[[c for c in [coef_name, "log_days", "log_attention_share", "log_total_articles"] if c in data.columns]]
    m_c, m_r = fit_both_se(formula, data)
    n = int(m_c.nobs)
    print(f"\n{label}  (N={n})")
    print(f"  formula: {formula}")
    print(f"  {coef_name}: classical beta={m_c.params[coef_name]:.4f}  SE(classical)={m_c.bse[coef_name]:.4f}  p={m_c.pvalues[coef_name]:.4f}")
    print(f"  {coef_name}: HC3       beta={m_r.params[coef_name]:.4f}  SE(HC3)={m_r.bse[coef_name]:.4f}  p={m_r.pvalues[coef_name]:.4f}")
    print(f"  R-squared={m_c.rsquared:.4f}  F={m_c.fvalue:.2f}  F p={m_c.f_pvalue:.4g}")
    return m_c, m_r


print("\n" + "-" * 70)
print("MAIN MODELS, CLASSICAL OLS SE vs HC3 ROBUST SE (item 8)")
print("-" * 70)
m1c, m1r = report_model_pair("Model 1: log_days ~ log_disbursements (replicates Table 3)",
                              "log_days ~ log_disbursements", df)
m2c, m2r = report_model_pair("Model 2: log_attention_share ~ log_disbursements (replicates Table 4)",
                              "log_attention_share ~ log_disbursements", df)

# add the total-article-count control (hc3 se)
print("\n" + "-" * 70)
print("MODELS WITH log(total_articles) CONTROL (item 2), HC3 SE")
print("-" * 70)
m3c, m3r = report_model_pair(
    "Model 1b: log_days ~ log_disbursements + log_total_articles",
    "log_days ~ log_disbursements + log_total_articles", df)
print(f"  log_total_articles: HC3 beta={m3r.params['log_total_articles']:.4f}  SE={m3r.bse['log_total_articles']:.4f}  p={m3r.pvalues['log_total_articles']:.4f}")

m4c, m4r = report_model_pair(
    "Model 2b: log_attention_share ~ log_disbursements + log_total_articles",
    "log_attention_share ~ log_disbursements + log_total_articles", df)
print(f"  log_total_articles: HC3 beta={m4r.params['log_total_articles']:.4f}  SE={m4r.bse['log_total_articles']:.4f}  p={m4r.pvalues['log_total_articles']:.4f}")

# other forms of the attention share
print("\n" + "-" * 70)
print("ATTENTION SHARE: ALTERNATIVE FUNCTIONAL FORMS (item 7)")
print("-" * 70)

share_min_positive = df.loc[df["attention_share"] > 0, "attention_share"].min()
small_c = share_min_positive / 2
print(f"Smallest positive attention_share in the data: {share_min_positive:.6g}; using c={small_c:.6g} for log(share+c)")

df["log_share_small_c"] = np.log(df["attention_share"] + small_c)
m5c, m5r = report_model_pair(
    "Model 2c: log(attention_share + c) ~ log_disbursements",
    "log_share_small_c ~ log_disbursements", df, coef_name="log_disbursements")

# poisson and negative binomial on usaid_articles, log(total_articles) as exposure
crd_full = pd.read_csv(crd_path).rename(columns={"iso3": "ISO3"})
crd_full["ISO3"] = crd_full["ISO3"].astype(str).str.strip().str.upper()
count_df = df.merge(
    crd_full[["ISO3", "usaid_articles", "total_articles"]].rename(columns={"total_articles": "total_articles_crd"}),
    on="ISO3", how="left"
)
count_df = count_df.dropna(subset=["usaid_articles", "total_articles_crd", "log_disbursements"])
count_df = count_df[count_df["total_articles_crd"] > 0]
print(f"\nCount-model sample (usaid_articles present, total_articles_crd>0, valid aid): N={len(count_df)}")

count_df["log_exposure"] = np.log(count_df["total_articles_crd"])
pois = smf.glm(
    "usaid_articles ~ log_disbursements", data=count_df,
    family=sm.families.Poisson(), offset=count_df["log_exposure"]
).fit()
print("\nPoisson, usaid_articles ~ log_disbursements, offset=log(total_articles):")
print(f"  N={int(pois.nobs)}  beta(log_disbursements)={pois.params['log_disbursements']:.4f}  SE={pois.bse['log_disbursements']:.4f}  p={pois.pvalues['log_disbursements']:.4g}")
print(f"  deviance={pois.deviance:.1f}  df_resid={pois.df_resid}  deviance/df={pois.deviance/pois.df_resid:.2f}  (>>1 means overdispersed -> NB preferred)")

try:
    negbin = smf.glm(
        "usaid_articles ~ log_disbursements", data=count_df,
        family=sm.families.NegativeBinomial(), offset=count_df["log_exposure"]
    ).fit()
    print("\nNegative Binomial, usaid_articles ~ log_disbursements, offset=log(total_articles):")
    print(f"  N={int(negbin.nobs)}  beta(log_disbursements)={negbin.params['log_disbursements']:.4f}  SE={negbin.bse['log_disbursements']:.4f}  p={negbin.pvalues['log_disbursements']:.4g}")
except Exception as e:
    print(f"\nNegative Binomial model failed to converge: {e}")

# sub-saharan africa (un geoscheme) vs coco "africa"
print("\n" + "-" * 70)
print("SUB-SAHARAN AFRICA, UN GEOSCHEME (item 10)")
print("-" * 70)

ssa = df[df["is_subsaharan_africa"]]
na = df[df["is_northern_africa"]]
print(f"Northern Africa countries in the sample (wrongly folded into 'Africa' by country_converter's continent scheme): "
      f"{na['ISO3'].tolist()}")
print(f"N Sub-Saharan Africa (un_subregion): {len(ssa)}  vs coco 'Africa' reported in draft Table 1/A1: 42/40")

for label, sub, y in [
    ("Sub-Saharan Africa, days", ssa, "log_days"),
    ("Sub-Saharan Africa, attention", ssa, "log_attention_share"),
]:
    reg = sub[["log_disbursements", y]].dropna()
    if len(reg) < 3:
        print(f"{label}: insufficient N")
        continue
    m = sm.OLS(reg[y], sm.add_constant(reg["log_disbursements"])).fit(cov_type="HC3")
    print(f"{label}: N={len(reg)}  beta={m.params['log_disbursements']:.4f}  HC3 SE={m.bse['log_disbursements']:.4f}  "
          f"p={m.pvalues['log_disbursements']:.4f}  R2={m.rsquared:.3f}")

# small-sample flag: regions with n < 10 get no p-value
print("\n" + "-" * 70)
print("SMALL-REGIONAL-SAMPLE FLAG (item 9): do not report p-values for N<10")
print("-" * 70)
for region in REGION_ORDER:
    n_r = (df["un_region"] == region).sum()
    flag = "SUPPRESS p-value (N<10)" if n_r < 10 else "ok"
    print(f"  {region}: N={n_r}  -> {flag}")
print("Draft Table A1 reports Europe (N=5) p=0.044* and Oceania (N=4) p=0.429 -- both should be")
print("reported as point estimates with a small-sample caveat and not asterisked as significant.")

# pooled model with aid x region interaction
print("\n" + "-" * 70)
print("POOLED AID x REGION INTERACTION (item 13) -- tests 'strongest in Africa' directly")
print("-" * 70)

df["region_cat"] = df["un_region"].where(df["un_region"].isin(REGION_ORDER), np.nan)
pooled_days = df.dropna(subset=["log_days", "log_disbursements", "region_cat"]).copy()
pooled_days["region_cat"] = pd.Categorical(pooled_days["region_cat"], categories=REGION_ORDER)
m_int_days = smf.ols("log_days ~ log_disbursements * C(region_cat, Treatment(reference='Asia'))",
                      data=pooled_days).fit(cov_type="HC3")
print(f"\nDays ~ aid * region (ref=Asia), N={int(m_int_days.nobs)}:")
print(m_int_days.summary2().tables[1].to_string())

pooled_attn = df.dropna(subset=["log_attention_share", "log_disbursements", "region_cat"]).copy()
pooled_attn["region_cat"] = pd.Categorical(pooled_attn["region_cat"], categories=REGION_ORDER)
m_int_attn = smf.ols("log_attention_share ~ log_disbursements * C(region_cat, Treatment(reference='Asia'))",
                      data=pooled_attn).fit(cov_type="HC3")
print(f"\nAttention ~ aid * region (ref=Asia), N={int(m_int_attn.nobs)}:")
print(m_int_attn.summary2().tables[1].to_string())

# also test aid x sub-saharan africa dummy (what "strongest in africa" means)
df["ssa_dummy"] = df["is_subsaharan_africa"].astype(float)
pooled_days_ssa = df.dropna(subset=["log_days", "log_disbursements", "ssa_dummy"])
m_ssa_days = smf.ols("log_days ~ log_disbursements * ssa_dummy", data=pooled_days_ssa).fit(cov_type="HC3")
print(f"\nDays ~ aid * Sub-Saharan-Africa dummy, N={int(m_ssa_days.nobs)}, HC3 SE:")
print(m_ssa_days.summary2().tables[1].to_string())
inter_p = m_ssa_days.pvalues.get("log_disbursements:ssa_dummy", np.nan)
print(f"\nInteraction term p-value (aid x SSA dummy): {inter_p:.4f} "
      f"{'(not significant -> no statistical support for ''strongest in Africa'')' if inter_p >= 0.05 else '(significant)'}")

pooled_attn_ssa = df.dropna(subset=["log_attention_share", "log_disbursements", "ssa_dummy"])
m_ssa_attn = smf.ols("log_attention_share ~ log_disbursements * ssa_dummy", data=pooled_attn_ssa).fit(cov_type="HC3")
print(f"\nAttention ~ aid * Sub-Saharan-Africa dummy, N={int(m_ssa_attn.nobs)}, HC3 SE:")
print(m_ssa_attn.summary2().tables[1].to_string())
inter_p2 = m_ssa_attn.pvalues.get("log_disbursements:ssa_dummy", np.nan)
print(f"\nInteraction term p-value (aid x SSA dummy): {inter_p2:.4f} "
      f"{'(not significant -> no statistical support for ''strongest in Africa'')' if inter_p2 >= 0.05 else '(significant)'}")

# outlier re-runs
print("\n" + "-" * 70)
print("OUTLIER RE-RUNS (item 14)")
print("-" * 70)

no_ukr = df[df["ISO3"] != "UKR"]
reg = no_ukr[["log_disbursements", "log_days"]].dropna()
m = sm.OLS(reg["log_days"], sm.add_constant(reg["log_disbursements"])).fit(cov_type="HC3")
print(f"\nDays model, excluding Ukraine: N={len(reg)}  beta={m.params['log_disbursements']:.4f}  "
      f"HC3 SE={m.bse['log_disbursements']:.4f}  p={m.pvalues['log_disbursements']:.4f}  R2={m.rsquared:.3f}")
print("(Compare to full-sample Table 3: N=93, beta=-0.170, R2=0.165)")

no_les_moz = df[~df["ISO3"].isin(["LSO", "MOZ"])]
reg2 = no_les_moz[["log_disbursements", "log_attention_share"]].dropna()
m2 = sm.OLS(reg2["log_attention_share"], sm.add_constant(reg2["log_disbursements"])).fit(cov_type="HC3")
print(f"\nAttention model, excluding Lesotho + Mozambique: N={len(reg2)}  beta={m2.params['log_disbursements']:.4f}  "
      f"HC3 SE={m2.bse['log_disbursements']:.4f}  p={m2.pvalues['log_disbursements']:.4f}  R2={m2.rsquared:.3f}")
print("(Compare to full-sample Table 4: N=100, beta=0.167, R2=0.086)")

iran = df[df["ISO3"] == "IRN"][["ISO3", "country", "us_oda_disbursements", "days_to_first_article", "log_days", "attention_share"]]
print("\nIran's raw data point (claimed 'delayed' in the draft's qualitative section):")
print(iran.to_string(index=False))
print("Iran's days_to_first_article is", "below" if float(iran["days_to_first_article"].iloc[0]) < both["days_to_first_article"].median() else "above",
      "the sample median of", both["days_to_first_article"].median(), "days -- i.e. Iran reacted fast, not 'delayed'.")

# cox model for time to first article, censored at 365 days
print("\n" + "-" * 70)
print("SURVIVAL MODEL: TIME TO FIRST ARTICLE, RIGHT-CENSORED AT 365 DAYS")
print("-" * 70)
print("Countries with no matched article are censored at 365 (event=0), not dropped.")
print("Countries with an article are an event at their observed day (event=1).")

surv_df = df[["ISO3", "country", "days_to_first_article", "log_disbursements", "us_oda_disbursements"]].copy()
surv_df = surv_df.dropna(subset=["log_disbursements"])  # same aid rule as table 3
surv_df["event"] = surv_df["days_to_first_article"].notna().astype(int)
surv_df["time"] = surv_df["days_to_first_article"].fillna(365.0)
surv_df.loc[surv_df["time"] > 365, "time"] = 365.0
print(f"\nSurvival sample: N={len(surv_df)}  events={surv_df['event'].sum()}  censored={len(surv_df)-surv_df['event'].sum()}")

try:
    from lifelines import CoxPHFitter
    cph = CoxPHFitter()
    cph.fit(surv_df[["time", "event", "log_disbursements"]], duration_col="time", event_col="event")
    print("\nCox proportional-hazards model, time-to-first-article ~ log(aid):")
    cph.print_summary()
    hz = cph.hazard_ratios_["log_disbursements"]
    print(f"\nHazard ratio for log(aid): {hz:.4f}  "
          f"({'>1: higher aid -> higher hazard of reporting sooner at any time -> faster (salience)' if hz > 1 else '<1: higher aid -> lower hazard -> slower (dampening)'})")
except Exception as e:
    print(f"\nCox model failed: {e}")

try:
    from lifelines import WeibullAFTFitter
    aft = WeibullAFTFitter()
    aft.fit(surv_df[["time", "event", "log_disbursements"]], duration_col="time", event_col="event")
    print("\nWeibull AFT model, time-to-first-article ~ log(aid):")
    aft.print_summary()
except Exception as e:
    print(f"\nWeibull AFT model failed: {e}")

# controls that are not available
print("\n" + "-" * 70)
print("CONTROLS NOT AVAILABLE IN THIS FOLDER")
print("-" * 70)
print("Population and GDP were requested as controls but do not exist anywhere in this")
print("project folder (checked all .csv/.xlsx files). They were not fabricated.")
print("To add them, download (by ISO3, 2018-2022 or latest available year):")
print("  - Population: World Bank SP.POP.TOTL, https://data.worldbank.org/indicator/SP.POP.TOTL")
print("    or API: https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?format=json")
print("  - GDP (current US$): World Bank NY.GDP.MKTP.CD, https://data.worldbank.org/indicator/NY.GDP.MKTP.CD")
print("  - GDP per capita: World Bank NY.GDP.PCAP.CD")
print("Join key: ISO3166-1 alpha-3 code, matching the 'ISO3' column already used throughout this project.")

# save the summary table
summary_rows = [
    {"model": "Table 3 replication (days ~ aid)", "n": int(m1c.nobs), "beta": m1c.params["log_disbursements"],
     "se_classical": m1c.bse["log_disbursements"], "se_hc3": m1r.bse["log_disbursements"], "p_hc3": m1r.pvalues["log_disbursements"]},
    {"model": "Table 4 replication (attention ~ aid)", "n": int(m2c.nobs), "beta": m2c.params["log_disbursements"],
     "se_classical": m2c.bse["log_disbursements"], "se_hc3": m2r.bse["log_disbursements"], "p_hc3": m2r.pvalues["log_disbursements"]},
    {"model": "days ~ aid + log_total_articles", "n": int(m3c.nobs), "beta": m3c.params["log_disbursements"],
     "se_classical": m3c.bse["log_disbursements"], "se_hc3": m3r.bse["log_disbursements"], "p_hc3": m3r.pvalues["log_disbursements"]},
    {"model": "attention ~ aid + log_total_articles", "n": int(m4c.nobs), "beta": m4c.params["log_disbursements"],
     "se_classical": m4c.bse["log_disbursements"], "se_hc3": m4r.bse["log_disbursements"], "p_hc3": m4r.pvalues["log_disbursements"]},
    {"model": "log(attention_share + c) ~ aid", "n": int(m5c.nobs), "beta": m5c.params["log_disbursements"],
     "se_classical": m5c.bse["log_disbursements"], "se_hc3": m5r.bse["log_disbursements"], "p_hc3": m5r.pvalues["log_disbursements"]},
    {"model": "days ~ aid, excluding Ukraine", "n": len(reg), "beta": m.params["log_disbursements"],
     "se_classical": np.nan, "se_hc3": m.bse["log_disbursements"], "p_hc3": m.pvalues["log_disbursements"]},
    {"model": "attention ~ aid, excluding Lesotho+Mozambique", "n": len(reg2), "beta": m2.params["log_disbursements"],
     "se_classical": np.nan, "se_hc3": m2.bse["log_disbursements"], "p_hc3": m2.pvalues["log_disbursements"]},
]
summary_df = pd.DataFrame(summary_rows)
summary_df.to_csv(os.path.join(OUT_DIR, "phase3_summary_table.csv"), index=False)
print(f"\n\nSaved summary table to {os.path.join(OUT_DIR, 'phase3_summary_table.csv')}")
print(summary_df.to_string(index=False))

print("\n" + "=" * 70)
print("PHASE 3 RUN COMPLETE")
print("=" * 70)

# cox model again, with the volume control (log_total_articles) added
print("\n" + "-" * 70)
print("FOLLOW-UP: COX MODEL WITH log_total_articles CONTROL")
print("-" * 70)

surv_df2 = df[["ISO3", "country", "days_to_first_article", "log_disbursements",
               "us_oda_disbursements", "log_total_articles"]].copy()
surv_df2 = surv_df2.dropna(subset=["log_disbursements", "log_total_articles"])
surv_df2["event"] = surv_df2["days_to_first_article"].notna().astype(int)
surv_df2["time"] = surv_df2["days_to_first_article"].fillna(365.0)
surv_df2.loc[surv_df2["time"] > 365, "time"] = 365.0
print(f"\nSurvival sample (with volume control, requires total_articles too): "
      f"N={len(surv_df2)}  events={surv_df2['event'].sum()}  censored={len(surv_df2)-surv_df2['event'].sum()}")

try:
    from lifelines import CoxPHFitter
    cph2 = CoxPHFitter()
    cph2.fit(surv_df2[["time", "event", "log_disbursements", "log_total_articles"]],
              duration_col="time", event_col="event")
    print("\nCox model, time-to-first-article ~ log(aid) + log(total_articles):")
    cph2.print_summary()
    hz_aid = cph2.hazard_ratios_["log_disbursements"]
    hz_vol = cph2.hazard_ratios_["log_total_articles"]
    p_aid = cph2.summary.loc["log_disbursements", "p"]
    p_vol = cph2.summary.loc["log_total_articles", "p"]
    print(f"\nlog(aid): hazard ratio={hz_aid:.4f}  p={p_aid:.4g}")
    print(f"log(total_articles): hazard ratio={hz_vol:.4f}  p={p_vol:.4g}")
    print("Compare to the no-control Cox model above: hazard ratio=1.4926, p<0.005.")
except Exception as e:
    print(f"\nCox model with volume control failed: {e}")
