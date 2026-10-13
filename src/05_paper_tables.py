# tables 1-4, a1-a2 and figures 1-2, a1-a2 (classical se, raw-row attention share)
# reads: data/input/3-29-v2_oda_data.csv
# writes: outputs/05_paper_tables/ (6 table csvs, 4 figure pngs, 2 data-check text files)
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

# outlier labels: ukraine, bangladesh and iran always, plus any country with a
# residual z-score of 2 or more (printed for each figure)
# attention share is shown per 1,000 in the tables. region rows with fewer than
# 10 countries get a small-sample caution
# data check: data_check_days_to_first_article.txt flags a repeated maximum (possible cap)

import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import country_converter as coco

# style
mpl.rcParams["font.family"] = "serif"
mpl.rcParams["font.serif"] = ["Garamond"]
sns.set_style("white")
mpl.rcParams["axes.spines.top"] = False
mpl.rcParams["axes.spines.right"] = False
mpl.rcParams["axes.edgecolor"] = "#333333"
mpl.rcParams["axes.labelcolor"] = "#222222"
mpl.rcParams["text.color"] = "#222222"
mpl.rcParams["xtick.color"] = "#333333"
mpl.rcParams["ytick.color"] = "#333333"

ACCENT = "#2C5F8A"      # single accent color for points and main line
GRAY   = "#8C8C8C"      # gray for secondary elements (region facets, appendix)
LINE   = "#1A1A1A"      # near-black for the fitted line in small multiples

ALWAYS_LABEL = {"UKR", "BGD", "IRN"}  # ukraine, bangladesh, iran: always labeled
OUTLIER_Z_THRESHOLD = 2.0  # also label countries with a residual z-score of this size or more

# ukraine ≈2,128.8 and kenya ≈795.2 in the csv only match real us aid totals
# if the unit is millions of us dollars
AID_UNIT = "US Dollars, millions"

# load data
BASE_DIR = os.path.dirname(__file__)
DATA_PATH = config.ODA_DATA
OUT_DIR = str(config.OUT_PAPER_TABLES)
os.makedirs(OUT_DIR, exist_ok=True)


def load_data():
    df = pd.read_csv(DATA_PATH)

    df["us_oda_disbursements"] = (
        df["us_oda_disbursements"].astype(str).str.replace(",", "")
    )
    df["us_oda_disbursements"] = pd.to_numeric(
        df["us_oda_disbursements"], errors="coerce"
    )
    df["days_to_first_article"] = pd.to_numeric(
        df["days_to_first_article"], errors="coerce"
    )
    df["attention_share"] = pd.to_numeric(df["attention_share"], errors="coerce")

    df["log_days"] = np.log1p(df["days_to_first_article"])

    df["log_disbursements"] = np.nan
    positive_mask = df["us_oda_disbursements"] > 0
    df.loc[positive_mask, "log_disbursements"] = np.log(
        df.loc[positive_mask, "us_oda_disbursements"]
    )
    df["log_attention_share"] = np.log1p(df["attention_share"])

    df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()
    df["region"] = coco.convert(names=df["ISO3"], to="continent")
    df["region"] = df["region"].replace(
        {"South America": "Americas", "North America": "Americas", "America": "Americas"}
    )
    df["region"] = df["region"].replace("not found", np.nan)
    df["region"] = df["region"].fillna("Other")

    return df


REGION_ORDER = ["Africa", "Americas", "Asia", "Europe", "Oceania"]

# plain-english labels for readers who are not statisticians
PLAIN_LABELS = {
    "log_disbursements": f"US Aid Amount (log, {AID_UNIT})",
    "log_days": "Days Until First News Article (log)",
    "log_attention_share": "Share of Global Media Attention (log)",
}


# regression helper
def run_regression(sub_df, x, y):
    reg_df = sub_df[[x, y]].dropna()
    if len(reg_df) < 3:
        return None
    X = sm.add_constant(reg_df[x])
    model = sm.OLS(reg_df[y], X).fit()
    return {
        "n": len(reg_df),
        "coef": model.params[x],
        "se": model.bse[x],
        "p": model.pvalues[x],
        "r2": model.rsquared,
        "f_stat": model.fvalue,
        "f_p": model.f_pvalue,
    }


def check_value_cap(df, raw_col, iso_col="ISO3"):
    """
    check whether the raw (pre-log) outcome has a repeated maximum value.
    a repeated maximum can mean the variable has an upper cap or a fill-in
    value (for example, 'no article found' coded as a fixed number of days).
    returns a small report string and the list of affected iso3 codes.
    """
    s = df[[iso_col, raw_col]].dropna()
    if len(s) == 0:
        return "No data to check.", []

    max_val = s[raw_col].max()
    at_max = s.loc[s[raw_col] == max_val, iso_col].tolist()

    top_counts = s[raw_col].value_counts().head(5)

    lines = [f"Highest value of '{raw_col}': {max_val}"]
    lines.append(f"Countries at this highest value ({len(at_max)}): {', '.join(at_max) if at_max else 'none'}")
    lines.append("Most common values (value: count):")
    for val, cnt in top_counts.items():
        lines.append(f"  {val}: {cnt}")

    if len(at_max) >= 3:
        lines.append(
            "WARNING: 3 or more countries share the same highest value. "
            "This pattern can mean the variable is capped, or that missing "
            "articles were filled in with a fixed placeholder value. "
            "Check the raw data source for this variable before treating "
            "these points as real, high, values."
        )

    return "\n".join(lines), at_max


def detect_statistical_outliers(df, x_col, y_col, iso_col="ISO3", z_thresh=OUTLIER_Z_THRESHOLD):
    """
    flag countries whose regression residual is more than z_thresh standard
    deviations from the fitted line. this finds outliers by their distance
    from the trend, rather than by a fixed, hand-picked list of countries.
    """
    reg_df = df[[iso_col, x_col, y_col]].dropna()
    if len(reg_df) < 3:
        return set()

    X = sm.add_constant(reg_df[x_col])
    model = sm.OLS(reg_df[y_col], X).fit()
    resid = model.resid
    resid_z = (resid - resid.mean()) / resid.std()

    flagged = reg_df.loc[resid_z.abs() >= z_thresh, iso_col]
    return set(flagged.tolist())


def diagnose_dropped_countries(df, y_col, x_col="log_disbursements", iso_col="ISO3"):
    """
    find countries that have a valid outcome value (used in the descriptive
    table) but are missing the aid value (so they drop out of the regression
    table). this explains any gap between the two tables' n.
    """
    has_y = set(df[[iso_col, y_col]].dropna()[iso_col])
    has_both = set(df[[iso_col, y_col, x_col]].dropna()[iso_col])
    dropped = sorted(has_y - has_both)
    return dropped


def sig_stars(p):
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    if p < 0.1:
        return "."
    return ""


# tables 1 and 2: descriptive stats by region
def make_descriptive_table(df, y_col, outcome_label, scale=1):
    rows = []
    subsets = [("All Countries", df)] + [(r, df[df["region"] == r]) for r in REGION_ORDER]
    for label, sub in subsets:
        s = sub[y_col].dropna() * scale
        if len(s) == 0:
            continue
        rows.append(
            {
                "Group": label,
                "Number of Countries": len(s),
                "Average": round(s.mean(), 2),
                "Spread (SD)": round(s.std(), 2),
                "Lowest": round(s.min(), 2),
                "Highest": round(s.max(), 2),
            }
        )
    table = pd.DataFrame(rows)
    table.insert(0, "Outcome", outcome_label)
    return table


# tables 3 and 4: main-text regression (all countries)
def make_main_regression_table(df, y_col, outcome_label, scale=1):
    stats = run_regression(df, "log_disbursements", y_col)
    if stats is None:
        return pd.DataFrame()
    row = {
        "Outcome": outcome_label,
        "Number of Countries": stats["n"],
        "Effect of Aid Amount": round(stats["coef"] * scale, 3),
        "Uncertainty (Std. Error)": round(stats["se"] * scale, 3),
        "How Well the Model Fits (R-squared)": round(stats["r2"], 3),
        "Overall Model Test (F-statistic)": round(stats["f_stat"], 2),
        "Statistical Significance": f"p={stats['p']:.3f}{sig_stars(stats['p'])}",
    }
    return pd.DataFrame([row])


# tables a1 and a2: regression by region
SMALL_SAMPLE_CUTOFF = 10  # rows with fewer countries than this get a caution note

def make_appendix_regression_table(df, y_col, outcome_label, scale=1):
    rows = []
    subsets = [("All Countries", df)] + [(r, df[df["region"] == r]) for r in REGION_ORDER]
    for label, sub in subsets:
        stats = run_regression(sub, "log_disbursements", y_col)
        if stats is None:
            rows.append(
                {
                    "Group": label,
                    "Number of Countries": len(sub),
                    "Effect of Aid Amount": "—",
                    "Uncertainty (Std. Error)": "—",
                    "How Well the Model Fits (R-squared)": "—",
                    "Overall Model Test (F-statistic)": "—",
                    "Statistical Significance": "Not enough data",
                    "Caution": "Small sample" if len(sub) < SMALL_SAMPLE_CUTOFF else "",
                }
            )
            continue
        rows.append(
            {
                "Group": label,
                "Number of Countries": stats["n"],
                "Effect of Aid Amount": round(stats["coef"] * scale, 3),
                "Uncertainty (Std. Error)": round(stats["se"] * scale, 3),
                "How Well the Model Fits (R-squared)": round(stats["r2"], 3),
                "Overall Model Test (F-statistic)": round(stats["f_stat"], 2),
                "Statistical Significance": f"p={stats['p']:.3f}{sig_stars(stats['p'])}",
                "Caution": f"Small sample (n={stats['n']})" if stats["n"] < SMALL_SAMPLE_CUTOFF else "",
            }
        )
    table = pd.DataFrame(rows)
    table.insert(0, "Outcome", outcome_label)
    return table


# outlier labels: ukraine, bangladesh, iran, plus countries far from the line
def label_outliers(ax, plot_df, x_col, y_col, extra_iso3=None):
    label_set = set(ALWAYS_LABEL) | (extra_iso3 or set())
    marked = plot_df[plot_df["ISO3"].isin(label_set)]
    for _, row in marked.iterrows():
        ax.annotate(
            row["ISO3"],
            (row[x_col], row[y_col]),
            textcoords="offset points",
            xytext=(6, 4),
            fontsize=9,
            color="#222222",
        )


def draw_reg_line(ax, sub, x_col, y_col, color, ci=True):
    reg_df = sub[[x_col, y_col]].dropna()
    if len(reg_df) < 3:
        return
    X = sm.add_constant(reg_df[x_col])
    model = sm.OLS(reg_df[y_col], X).fit()
    x_range = np.linspace(reg_df[x_col].min(), reg_df[x_col].max(), 200)
    y_pred = model.params["const"] + model.params[x_col] * x_range
    ax.plot(x_range, y_pred, color=color, linewidth=2)
    if ci:
        pred = model.get_prediction(sm.add_constant(pd.DataFrame({x_col: x_range})))
        ci_df = pred.conf_int(alpha=0.05)
        ax.fill_between(x_range, ci_df[:, 0], ci_df[:, 1], color=color, alpha=0.12)


# figures 1 and 2: main-text figures
def make_main_figure(df, y_col, title, ylabel, filename):
    plot_df = df[["log_disbursements", y_col, "ISO3"]].dropna()

    stat_outliers = detect_statistical_outliers(plot_df, "log_disbursements", y_col)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.scatter(
        plot_df["log_disbursements"], plot_df[y_col],
        color=ACCENT, alpha=0.55, s=45, edgecolor="none",
    )
    draw_reg_line(ax, plot_df, "log_disbursements", y_col, color=ACCENT)
    label_outliers(ax, plot_df, "log_disbursements", y_col, extra_iso3=stat_outliers)

    new_outliers = stat_outliers - ALWAYS_LABEL
    if new_outliers:
        print(f"[{filename}] Additional outliers found (>{OUTLIER_Z_THRESHOLD} SD from trend): {sorted(new_outliers)}")

    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(PLAIN_LABELS["log_disbursements"], fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.6)

    fig.text(
        0.5, -0.03,
        "Note: Labeled points are countries with unusual media response relative to aid received.",
        ha="center", fontsize=8, style="italic", color="dimgray",
    )

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, filename)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


# figures a1 and a2: small multiples by region
def make_appendix_figure(df, y_col, title, ylabel, filename):
    plot_df = df[["log_disbursements", y_col, "ISO3", "region"]].dropna()
    regions = [r for r in REGION_ORDER if len(plot_df[plot_df["region"] == r]) >= 3]

    fig, axes = plt.subplots(1, len(regions), figsize=(4 * len(regions), 4.2), sharey=True)
    if len(regions) == 1:
        axes = [axes]

    for ax, region in zip(axes, regions):
        sub = plot_df[plot_df["region"] == region]
        stat_outliers = detect_statistical_outliers(sub, "log_disbursements", y_col)
        ax.scatter(sub["log_disbursements"], sub[y_col], color=GRAY, alpha=0.6, s=35, edgecolor="none")
        draw_reg_line(ax, sub, "log_disbursements", y_col, color=LINE, ci=False)
        label_outliers(ax, sub, "log_disbursements", y_col, extra_iso3=stat_outliers)
        ax.set_title(region, fontsize=10, fontweight="bold")
        ax.grid(axis="y", color="#EAEAEA", linewidth=0.6)

    axes[0].set_ylabel(ylabel, fontsize=9)
    fig.suptitle(title, fontsize=12, fontweight="bold", y=1.03)

    plt.tight_layout(rect=[0, 0.08, 1, 1])
    fig.text(
        0.5, 0.02,
        PLAIN_LABELS["log_disbursements"],
        ha="center", fontsize=9,
    )

    out_path = os.path.join(OUT_DIR, filename)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


# run everything
def main():
    df = load_data()

    # data check: possible cap on days_to_first_article
    cap_report, capped_countries = check_value_cap(df, "days_to_first_article")
    with open(os.path.join(OUT_DIR, "data_check_days_to_first_article.txt"), "w") as f:
        f.write(cap_report)
    print("\n--- Data check: days_to_first_article ---")
    print(cap_report)

    # data check: why the descriptive n and the regression n differ
    dropped_days = diagnose_dropped_countries(df, "log_days")
    dropped_attn = diagnose_dropped_countries(df, "log_attention_share")
    print("\n--- Data check: countries dropped from regression (missing aid value) ---")
    print(f"Days to First News Article: {dropped_days if dropped_days else 'none'}")
    print(f"Share of Global Media Attention: {dropped_attn if dropped_attn else 'none'}")
    with open(os.path.join(OUT_DIR, "data_check_dropped_countries.txt"), "w") as f:
        f.write(
            "Countries with a valid outcome value but no valid aid value.\n"
            "These countries appear in the descriptive tables (Table 1, Table 2)\n"
            "but not in the regression tables (Table 3, Table 4, Table A1, Table A2).\n\n"
            f"Days to First News Article: {dropped_days if dropped_days else 'none'}\n"
            f"Share of Global Media Attention: {dropped_attn if dropped_attn else 'none'}\n"
        )

    # main-text tables
    table1 = make_descriptive_table(df, "log_days", "Days Until First News Article")
    table2 = make_descriptive_table(
        df, "log_attention_share", "Share of Global Media Attention (per 1,000)", scale=1000
    )
    table3 = make_main_regression_table(df, "log_days", "Days Until First News Article")
    table4 = make_main_regression_table(
        df, "log_attention_share", "Share of Global Media Attention (per 1,000)", scale=1000
    )

    # appendix tables
    table_a1 = make_appendix_regression_table(df, "log_days", "Days Until First News Article")
    table_a2 = make_appendix_regression_table(
        df, "log_attention_share", "Share of Global Media Attention (per 1,000)", scale=1000
    )

    table1.to_csv(os.path.join(OUT_DIR, "table1_descriptive_days.csv"), index=False)
    table2.to_csv(os.path.join(OUT_DIR, "table2_descriptive_attention.csv"), index=False)
    table3.to_csv(os.path.join(OUT_DIR, "table3_regression_days_main.csv"), index=False)
    table4.to_csv(os.path.join(OUT_DIR, "table4_regression_attention_main.csv"), index=False)
    table_a1.to_csv(os.path.join(OUT_DIR, "tableA1_regression_days_by_region.csv"), index=False)
    table_a2.to_csv(os.path.join(OUT_DIR, "tableA2_regression_attention_by_region.csv"), index=False)

    # main-text figures
    make_main_figure(
        df, "log_days",
        title="US Aid and Speed of Media Coverage",
        ylabel=PLAIN_LABELS["log_days"],
        filename="figure1_days_main.png",
    )
    make_main_figure(
        df, "log_attention_share",
        title="US Aid and Share of Media Attention",
        ylabel=PLAIN_LABELS["log_attention_share"],
        filename="figure2_attention_main.png",
    )

    # appendix figures
    make_appendix_figure(
        df, "log_days",
        title="US Aid and Speed of Media Coverage, by Region",
        ylabel=PLAIN_LABELS["log_days"],
        filename="figureA1_days_by_region.png",
    )
    make_appendix_figure(
        df, "log_attention_share",
        title="US Aid and Share of Media Attention, by Region",
        ylabel=PLAIN_LABELS["log_attention_share"],
        filename="figureA2_attention_by_region.png",
    )

    print("Done. Files saved to:", OUT_DIR)
    print("\n--- Table 3 (main text) ---")
    print(table3.to_string(index=False))
    print("\n--- Table 4 (main text) ---")
    print(table4.to_string(index=False))


if __name__ == "__main__":
    main()