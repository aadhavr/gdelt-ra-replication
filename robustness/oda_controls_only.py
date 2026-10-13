# control checks: v-dem press freedom (tables 5, 6, a3, figures 3, 4) and voeten
# us alignment (tables 7-10, a4, a5, figures 5, 6)
# reads: data/input/ (3-29-v2_oda_data.csv, vdem_filtered.csv, idealpoint_filtered.csv)
# writes: outputs/oda_controls_only/
# import config.py from the repo root
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

# both control files are averaged over 2018-2022
# figure 6: the interaction is not significant, it is shown for transparency

import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import statsmodels.api as sm

# font: plain sans-serif (arial), with fallbacks if arial is missing
mpl.rcParams["font.family"] = "sans-serif"
mpl.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "DejaVu Sans"]
mpl.rcParams["axes.spines.top"] = False
mpl.rcParams["axes.spines.right"] = False
mpl.rcParams["axes.edgecolor"] = "#333333"
mpl.rcParams["axes.labelcolor"] = "#222222"
mpl.rcParams["text.color"] = "#222222"
mpl.rcParams["xtick.color"] = "#333333"
mpl.rcParams["ytick.color"] = "#333333"

ACCENT = "#2C5F8A"       # high alignment / low censorship
LOW_COLOR = "#B0562E"    # low alignment / high censorship
GRAY = "#8C8C8C"

AID_UNIT = "US Dollars, millions"
CONTROL_YEAR_START = 2018
CONTROL_YEAR_END = 2022
SMALL_SAMPLE_CUTOFF = 10

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = config.ODA_DATA
IDEALPOINT_PATH = config.IDEALPOINT_FILTERED
VDEM_PATH = config.VDEM_FILTERED
OUT_DIR = str(config.OUT_CONTROLS)
os.makedirs(OUT_DIR, exist_ok=True)

PLAIN_LABELS = {
    "log_disbursements": f"US Aid Amount (log, {AID_UNIT})",
    "log_days": "Days Until First News Article (log)",
    "log_attention_share": "Share of Global Media Attention (log)",
}

REGION_ORDER = ["Africa", "Americas", "Asia", "Europe", "Oceania"]


# load data
def load_press_freedom():
    """v-dem press-freedom variables, averaged 2018-2022. one row per iso3."""
    vd = pd.read_csv(VDEM_PATH)
    years = range(CONTROL_YEAR_START, CONTROL_YEAR_END + 1)
    vd_window = vd[vd["year"].isin(years)]
    vd_avg = vd_window.groupby("country_text_id", as_index=False)[
        ["v2mecenefm", "v2meharjrn"]
    ].mean()
    return vd_avg.rename(columns={
        "country_text_id": "ISO3",
        "v2mecenefm": "press_censorship",
        "v2meharjrn": "journalist_harassment",
    })


def load_us_alignment():
    """voeten un-voting alignment with the us, averaged 2018-2022. one row per iso3."""
    ip = pd.read_csv(IDEALPOINT_PATH)
    years = range(CONTROL_YEAR_START, CONTROL_YEAR_END + 1)
    ip_window = ip[ip["year"].isin(years)]
    ip_avg = (
        ip_window.groupby("iso3c", as_index=False)["IdealPointFP"]
        .mean()
        .rename(columns={"IdealPointFP": "idealpoint_avg"})
    )
    us_score = ip_avg.loc[ip_avg["iso3c"] == "USA", "idealpoint_avg"]
    if len(us_score) == 0:
        raise ValueError("No USA row found in the ideal point file for this year window.")
    us_score = us_score.values[0]
    ip_avg["us_alignment"] = -(ip_avg["idealpoint_avg"] - us_score).abs()
    return ip_avg[["iso3c", "us_alignment"]].rename(columns={"iso3c": "ISO3"})


def load_data():
    df = pd.read_csv(DATA_PATH)

    df["us_oda_disbursements"] = df["us_oda_disbursements"].astype(str).str.replace(",", "")
    df["us_oda_disbursements"] = pd.to_numeric(df["us_oda_disbursements"], errors="coerce")
    df["days_to_first_article"] = pd.to_numeric(df["days_to_first_article"], errors="coerce")
    df["attention_share"] = pd.to_numeric(df["attention_share"], errors="coerce")

    df["log_days"] = np.log1p(df["days_to_first_article"])
    df["log_disbursements"] = np.nan
    positive_mask = df["us_oda_disbursements"] > 0
    df.loc[positive_mask, "log_disbursements"] = np.log(df.loc[positive_mask, "us_oda_disbursements"])
    df["log_attention_share"] = np.log1p(df["attention_share"])

    df["ISO3"] = df["ISO3"].astype(str).str.strip().str.upper()

    import country_converter as coco
    df["region"] = coco.convert(names=df["ISO3"], to="continent")
    df["region"] = df["region"].replace(
        {"South America": "Americas", "North America": "Americas", "America": "Americas"}
    )
    df["region"] = df["region"].replace("not found", np.nan)
    df["region"] = df["region"].fillna("Other")

    df = df.merge(load_press_freedom(), on="ISO3", how="left")
    df = df.merge(load_us_alignment(), on="ISO3", how="left")
    df["aid_x_alignment"] = df["log_disbursements"] * df["us_alignment"]

    # centered alignment: 0 is now a typical country, not one identical to the us.
    # this does not change the interaction, its p-value or r2. it only makes the main
    # aid effect the effect for an average-alignment country
    df["us_alignment_centered"] = df["us_alignment"] - df["us_alignment"].mean()
    df["aid_x_alignment_centered"] = df["log_disbursements"] * df["us_alignment_centered"]

    return df


# regression helpers
def sig_stars(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.1:   return "."
    return ""


def run_regression(sub_df, x, y):
    reg_df = sub_df[[x, y]].dropna()
    if len(reg_df) < 3:
        return None
    X = sm.add_constant(reg_df[x])
    model = sm.OLS(reg_df[y], X).fit()
    return {"n": len(reg_df), "coef": model.params[x], "p": model.pvalues[x], "r2": model.rsquared}


def run_multi_regression(sub_df, y, x_cols):
    reg_df = sub_df[[y] + x_cols].dropna()
    if len(reg_df) < len(x_cols) + 2:
        return None, None
    X = sm.add_constant(reg_df[x_cols])
    model = sm.OLS(reg_df[y], X).fit()
    return model, reg_df


def format_cell(coef, p, scale=1):
    if coef is None:
        return ""
    return f"{coef * scale:.3f}{sig_stars(p)}"


def get_param(model, param):
    if model is None or param not in model.params:
        return None, None
    return model.params[param], model.pvalues[param]


# press freedom checks (v-dem)
def make_press_freedom_table(df, y_col, outcome_label, scale=1):
    """table 5 / table 6 / one row of table a3: aid only vs. aid + press freedom."""
    m1 = run_regression(df, "log_disbursements", y_col)
    m2, reg2 = run_multi_regression(df, y_col, ["log_disbursements", "press_censorship", "journalist_harassment"])

    rows = [
        {
            "Statistic": "Number of countries",
            "Model 1: Aid only": m1["n"] if m1 else "",
            "Model 2: + press freedom (V-Dem)": len(reg2) if reg2 is not None else "",
        },
        {
            "Statistic": "Aid effect",
            "Model 1: Aid only": format_cell(m1["coef"], m1["p"], scale) if m1 else "",
            "Model 2: + press freedom (V-Dem)": format_cell(*get_param(m2, "log_disbursements"), scale),
        },
        {
            "Statistic": "Press censorship effect",
            "Model 1: Aid only": "",
            "Model 2: + press freedom (V-Dem)": format_cell(*get_param(m2, "press_censorship"), scale),
        },
        {
            "Statistic": "Journalist harassment effect",
            "Model 1: Aid only": "",
            "Model 2: + press freedom (V-Dem)": format_cell(*get_param(m2, "journalist_harassment"), scale),
        },
        {
            "Statistic": "R-squared",
            "Model 1: Aid only": round(m1["r2"], 3) if m1 else "",
            "Model 2: + press freedom (V-Dem)": round(m2.rsquared, 3) if m2 else "",
        },
    ]
    table = pd.DataFrame(rows)
    table.insert(0, "Outcome", outcome_label)
    return table


def make_press_freedom_region_table(df, y_col, outcome_label, scale=1):
    """table a3: press freedom robustness, broken out by region."""
    rows = []
    subsets = [("All Countries", df)] + [(r, df[df["region"] == r]) for r in REGION_ORDER]
    for label, sub in subsets:
        m2, reg2 = run_multi_regression(sub, y_col, ["log_disbursements", "press_censorship", "journalist_harassment"])
        n = len(reg2) if reg2 is not None else len(sub)
        coef, p = get_param(m2, "log_disbursements")
        rows.append({
            "Group": label,
            "Number of countries": n,
            "Aid effect (with press freedom control)": format_cell(coef, p, scale),
            "R-squared": round(m2.rsquared, 3) if m2 else "",
            "Caution": f"Small sample (n={n})" if n < SMALL_SAMPLE_CUTOFF else "",
        })
    table = pd.DataFrame(rows)
    table.insert(0, "Outcome", outcome_label)
    return table


def make_press_freedom_figure(df, y_col, title, ylabel, filename):
    """figure 3 / 4: small multiples by press-censorship tercile (low/medium/high)."""
    plot_df = df[["log_disbursements", "press_censorship", y_col, "ISO3"]].dropna()
    plot_df = plot_df.copy()
    plot_df["tercile"] = pd.qcut(plot_df["press_censorship"], 3, labels=["Low censorship", "Medium censorship", "High censorship"])

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), sharey=True)
    for ax, tier in zip(axes, ["Low censorship", "Medium censorship", "High censorship"]):
        sub = plot_df[plot_df["tercile"] == tier]
        ax.scatter(sub["log_disbursements"], sub[y_col], color=GRAY, alpha=0.6, s=35, edgecolor="none")
        reg_df = sub[["log_disbursements", y_col]].dropna()
        if len(reg_df) >= 3:
            X = sm.add_constant(reg_df["log_disbursements"])
            model = sm.OLS(reg_df[y_col], X).fit()
            x_range = np.linspace(reg_df["log_disbursements"].min(), reg_df["log_disbursements"].max(), 100)
            y_pred = model.params["const"] + model.params["log_disbursements"] * x_range
            ax.plot(x_range, y_pred, color=ACCENT, linewidth=2)
        ax.set_title(f"{tier}\n(n={len(sub)})", fontsize=10, fontweight="bold")
        ax.grid(axis="y", color="#EAEAEA", linewidth=0.6)

    axes[0].set_ylabel(ylabel, fontsize=9)
    fig.suptitle(title, fontsize=12, fontweight="bold", y=1.03)
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    fig.text(0.5, 0.01, PLAIN_LABELS["log_disbursements"], ha="center", fontsize=9)

    out_path = os.path.join(OUT_DIR, filename)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


# us alignment checks (voeten)
def make_alignment_table(df, y_col, outcome_label, scale=1):
    """
    table 7 / table 8: aid only vs. aid + us alignment interaction.
    uses the centered alignment variable, so "aid effect" in model 3 reads
    as the aid effect for a country at the average alignment level, not a
    country identical to the us. the interaction term itself, its p-value,
    and r-squared are unchanged by centering.
    """
    m1 = run_regression(df, "log_disbursements", y_col)
    m3, reg3 = run_multi_regression(df, y_col, ["log_disbursements", "us_alignment_centered", "aid_x_alignment_centered"])

    rows = [
        {
            "Statistic": "Number of countries",
            "Model 1: Aid only": m1["n"] if m1 else "",
            "Model 3: + US alignment (Voeten, centered)": len(reg3) if reg3 is not None else "",
        },
        {
            "Statistic": "Aid effect (at average alignment)",
            "Model 1: Aid only": format_cell(m1["coef"], m1["p"], scale) if m1 else "",
            "Model 3: + US alignment (Voeten, centered)": format_cell(*get_param(m3, "log_disbursements"), scale),
        },
        {
            "Statistic": "US alignment effect",
            "Model 1: Aid only": "",
            "Model 3: + US alignment (Voeten, centered)": format_cell(*get_param(m3, "us_alignment_centered"), scale),
        },
        {
            "Statistic": "Aid x US alignment effect",
            "Model 1: Aid only": "",
            "Model 3: + US alignment (Voeten, centered)": format_cell(*get_param(m3, "aid_x_alignment_centered"), scale),
        },
        {
            "Statistic": "R-squared",
            "Model 1: Aid only": round(m1["r2"], 3) if m1 else "",
            "Model 3: + US alignment (Voeten, centered)": round(m3.rsquared, 3) if m3 else "",
        },
    ]
    table = pd.DataFrame(rows)
    table.insert(0, "Outcome", outcome_label)
    return table


def make_alignment_region_drop_table(df, y_col, outcome_label, scale=1):
    """
    table a5: robustness to dropping europe and/or oceania from the pooled
    interaction. europe has only 5 countries and a very high r-squared in
    its own regional regression (table a4) -- a classic sign that a small
    number of points may be driving the pooled result. this checks that.
    """
    rows = []
    tests = [
        ("All regions", df),
        ("Excluding Europe", df[df["region"] != "Europe"]),
        ("Excluding Europe and Oceania", df[~df["region"].isin(["Europe", "Oceania"])]),
    ]
    for label, sub in tests:
        m3, reg3 = run_multi_regression(sub, y_col, ["log_disbursements", "us_alignment_centered", "aid_x_alignment_centered"])
        n = len(reg3) if reg3 is not None else len(sub)
        coef, p = get_param(m3, "aid_x_alignment_centered")
        rows.append({
            "Sample": label,
            "Number of countries": n,
            "Aid x alignment effect": format_cell(coef, p, scale),
            "R-squared": round(m3.rsquared, 3) if m3 else "",
        })
    table = pd.DataFrame(rows)
    table.insert(0, "Outcome", outcome_label)
    return table


def compute_simple_slopes(df, y_col):
    """
    shared math for both table 9/10 and figure 5/6: the exact aid effect,
    its standard error, and its significance at the 10th and 90th
    percentile of us alignment. returns none if the model can't be fit.
    """
    model, reg_df = run_multi_regression(df, y_col, ["log_disbursements", "us_alignment", "aid_x_alignment"])
    if model is None:
        return None

    from scipy import stats as sstats
    cov = model.cov_params()
    b_aid = model.params["log_disbursements"]
    b_inter = model.params["aid_x_alignment"]
    var_aid = cov.loc["log_disbursements", "log_disbursements"]
    var_inter = cov.loc["aid_x_alignment", "aid_x_alignment"]
    cov_ai = cov.loc["log_disbursements", "aid_x_alignment"]
    dof = model.df_resid

    results = {}
    for key, q in [("low", 0.10), ("high", 0.90)]:
        a = reg_df["us_alignment"].quantile(q)
        effect = b_aid + b_inter * a
        se = np.sqrt(var_aid + (a**2) * var_inter + 2 * a * cov_ai)
        t = effect / se
        p = 2 * (1 - sstats.t.cdf(abs(t), dof))
        results[key] = {"alignment": a, "effect": effect, "se": se, "p": p}
    results["model"] = model
    results["reg_df"] = reg_df
    return results


def make_simple_slope_table(df, y_col, outcome_label, scale=1):
    """
    table 9 / table 10: the exact aid effect, its standard error, and its
    significance at the 10th and 90th percentile of us alignment -- the
    two lines drawn in figure 5 / figure 6. answers directly: does the aid
    effect survive at the low-alignment end, or does it disappear there?
    """
    slopes = compute_simple_slopes(df, y_col)
    if slopes is None:
        return pd.DataFrame()

    rows = []
    for key, label in [("low", "Low US alignment (10th pct.)"), ("high", "High US alignment (90th pct.)")]:
        s = slopes[key]
        rows.append({
            "Alignment level": label,
            "Alignment score": round(s["alignment"], 3),
            "Aid effect": format_cell(s["effect"], s["p"], scale),
            "Standard error": round(s["se"] * scale, 3),
        })
    table = pd.DataFrame(rows)
    table.insert(0, "Outcome", outcome_label)
    return table


def make_alignment_region_table(df, y_col, outcome_label, scale=1):
    """table a4: us alignment interaction, broken out by region."""
    rows = []
    subsets = [("All Countries", df)] + [(r, df[df["region"] == r]) for r in REGION_ORDER]
    for label, sub in subsets:
        m3, reg3 = run_multi_regression(sub, y_col, ["log_disbursements", "us_alignment", "aid_x_alignment"])
        n = len(reg3) if reg3 is not None else len(sub)
        coef, p = get_param(m3, "aid_x_alignment")
        rows.append({
            "Group": label,
            "Number of countries": n,
            "Aid x alignment effect": format_cell(coef, p, scale),
            "R-squared": round(m3.rsquared, 3) if m3 else "",
            "Caution": f"Small sample (n={n})" if n < SMALL_SAMPLE_CUTOFF else "",
        })
    table = pd.DataFrame(rows)
    table.insert(0, "Outcome", outcome_label)
    return table


def make_alignment_figure(df, y_col, title, ylabel, filename, note=None, scale=1):
    """
    figure 5 / 6: aid effect at low vs. high us alignment (simple slopes).
    the effect size, standard error, and significance are printed right
    next to each line's endpoint, not tucked into the legend.
    """
    plot_df = df[["log_disbursements", "us_alignment", y_col, "ISO3"]].dropna()
    slopes = compute_simple_slopes(df, y_col)
    if slopes is None:
        print(f"[{filename}] Not enough data to fit the interaction model - figure skipped.")
        return None
    model = slopes["model"]

    x_range = np.linspace(plot_df["log_disbursements"].min(), plot_df["log_disbursements"].max(), 200)
    y_span = plot_df[y_col].max() - plot_df[y_col].min()
    anchor_idx = -15

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.scatter(plot_df["log_disbursements"], plot_df[y_col], color=GRAY, alpha=0.35, s=35, edgecolor="none")

    def line_y(key):
        s = slopes[key]
        align_val = s["alignment"]
        return (
            model.params["const"]
            + model.params["log_disbursements"] * x_range
            + model.params["us_alignment"] * align_val
            + model.params["aid_x_alignment"] * x_range * align_val
        )

    y_low_full = line_y("low")
    y_high_full = line_y("high")

    # push the labels apart based on where the lines sit at the anchor point,
    # since the two lines can cross
    low_is_higher = y_low_full[anchor_idx] >= y_high_full[anchor_idx]
    offset_sign = {"low": 1 if low_is_higher else -1, "high": -1 if low_is_higher else 1}
    # keep a minimum gap between the two labels
    line_gap = abs(y_low_full[anchor_idx] - y_high_full[anchor_idx])
    push = max(0.09 * y_span, 0.6 * line_gap + 0.05 * y_span)

    for key, color, level_label in [
        ("low", LOW_COLOR, "Low US alignment (10th pct.)"),
        ("high", ACCENT, "High US alignment (90th pct.)"),
    ]:
        s = slopes[key]
        y_pred = y_low_full if key == "low" else y_high_full
        ax.plot(x_range, y_pred, color=color, linewidth=2.2, label=level_label)

        stars = sig_stars(s["p"])
        p_str = f"p<0.001{stars}" if s["p"] < 0.001 else f"p={s['p']:.3f}{stars}"
        stat_text = f"b={s['effect']*scale:.3f} (SE={s['se']*scale:.3f})\n{p_str}"

        anchor_x = x_range[anchor_idx]
        anchor_y = y_pred[anchor_idx] + offset_sign[key] * push
        ax.annotate(
            stat_text,
            xy=(anchor_x, y_pred[anchor_idx]),
            xytext=(anchor_x, anchor_y),
            color=color,
            fontsize=8.5,
            fontweight="bold",
            ha="right",
            va="center",
            linespacing=1.4,
        )

    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(PLAIN_LABELS["log_disbursements"], fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.6)
    ax.legend(fontsize=9, frameon=False, loc="upper right" if y_col == "log_days" else "upper left")

    default_note = "Note: Lines show the fitted aid effect at the 10th and 90th percentile of US voting alignment, with its standard error and significance."
    fig.text(0.5, -0.03, note or default_note, ha="center", fontsize=8, style="italic", color="dimgray")

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, filename)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


# run everything
def main():
    df = load_data()

    # press freedom
    table5 = make_press_freedom_table(df, "log_days", "Days Until First News Article")
    table6 = make_press_freedom_table(df, "log_attention_share", "Share of Global Media Attention (per 1,000)", scale=1000)
    table_a3 = make_press_freedom_region_table(df, "log_days", "Days Until First News Article")

    table5.to_csv(os.path.join(OUT_DIR, "table5_press_freedom_days.csv"), index=False)
    table6.to_csv(os.path.join(OUT_DIR, "table6_press_freedom_attention.csv"), index=False)
    table_a3.to_csv(os.path.join(OUT_DIR, "tableA3_press_freedom_by_region.csv"), index=False)

    make_press_freedom_figure(
        df, "log_days",
        title="Aid and Speed of Coverage, by Press Censorship Level (V-Dem)",
        ylabel=PLAIN_LABELS["log_days"],
        filename="figure3_press_freedom_days.png",
    )
    make_press_freedom_figure(
        df, "log_attention_share",
        title="Aid and Media Attention, by Press Censorship Level (V-Dem)",
        ylabel=PLAIN_LABELS["log_attention_share"],
        filename="figure4_press_freedom_attention.png",
    )

    # us alignment
    table7 = make_alignment_table(df, "log_days", "Days Until First News Article")
    table8 = make_alignment_table(df, "log_attention_share", "Share of Global Media Attention (per 1,000)", scale=1000)
    table_a4 = make_alignment_region_table(df, "log_days", "Days Until First News Article")
    table_a5 = make_alignment_region_drop_table(df, "log_days", "Days Until First News Article")
    table9 = make_simple_slope_table(df, "log_days", "Days Until First News Article")
    table10 = make_simple_slope_table(df, "log_attention_share", "Share of Global Media Attention (per 1,000)", scale=1000)

    table7.to_csv(os.path.join(OUT_DIR, "table7_alignment_days.csv"), index=False)
    table8.to_csv(os.path.join(OUT_DIR, "table8_alignment_attention.csv"), index=False)
    table_a4.to_csv(os.path.join(OUT_DIR, "tableA4_alignment_by_region.csv"), index=False)
    table_a5.to_csv(os.path.join(OUT_DIR, "tableA5_alignment_drop_europe_oceania.csv"), index=False)
    table9.to_csv(os.path.join(OUT_DIR, "table9_simple_slopes_days.csv"), index=False)
    table10.to_csv(os.path.join(OUT_DIR, "table10_simple_slopes_attention.csv"), index=False)

    make_alignment_figure(
        df, "log_days",
        title="Aid Effect on Speed of Coverage, by US Alignment (Voeten)",
        ylabel=PLAIN_LABELS["log_days"],
        filename="figure5_alignment_days.png",
    )
    make_alignment_figure(
        df, "log_attention_share",
        title="Aid Effect on Media Attention, by US Alignment (Voeten)",
        ylabel=PLAIN_LABELS["log_attention_share"],
        filename="figure6_alignment_attention.png",
        note="Note: This interaction was NOT statistically significant. Shown for transparency.",
        scale=1000,
    )

    print("Done. Files saved to:", OUT_DIR)
    print("\n=== CHECK 1: PRESS FREEDOM (V-Dem) ===")
    print("\n--- Table 5 ---")
    print(table5.to_string(index=False))
    print("\n--- Table 6 ---")
    print(table6.to_string(index=False))
    print("\n--- Table A3 (by region) ---")
    print(table_a3.to_string(index=False))

    print("\n=== CHECK 2: US ALIGNMENT (Voeten) ===")
    align = df["us_alignment"].dropna()
    print(f"\n--- Alignment variable diagnostic ---")
    print(f"N countries with alignment score: {len(align)}")
    print(f"Mean: {align.mean():.4f}   Min: {align.min():.4f}   Max: {align.max():.4f}")
    print("Coding: 0 = identical to the US (max alignment). More negative = further from the US.")
    print("\n--- Table 7 (centered) ---")
    print(table7.to_string(index=False))
    print("\n--- Table 8 (centered) ---")
    print(table8.to_string(index=False))
    print("\n--- Table A4 (by region) ---")
    print(table_a4.to_string(index=False))
    print("\n--- Table A5 (robustness: dropping Europe / Oceania) ---")
    print(table_a5.to_string(index=False))
    print("\n--- Table 9 (simple slopes, days) ---")
    print(table9.to_string(index=False))
    print("\n--- Table 10 (simple slopes, attention) ---")
    print(table10.to_string(index=False))


if __name__ == "__main__":
    main()