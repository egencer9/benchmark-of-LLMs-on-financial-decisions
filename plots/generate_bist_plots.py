"""
BIST30 LLM Benchmark — Plot Generator
Mevcut JSON sonuçlarından grafikleri oluşturur ve PNG olarak kaydeder.
Çalıştırma: python plots/generate_bist_plots.py
"""

import json
import os
import sys
import glob
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import FuncFormatter

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR  = os.path.join(PROJECT_ROOT, "data", "results", "BIST30")
OUT_DIR      = os.path.join(PROJECT_ROOT, "plots", "output")
os.makedirs(OUT_DIR, exist_ok=True)

# ─── Style ────────────────────────────────────────────────────────────────────
# Aliases to exclude (broken runs, 404 API errors, etc.)
EXCLUDE_ALIASES = [
    "anthropic/claude-3.7-sonnet",
    "claude-3.7-sonnet",
]

PALETTE = [
    "#4C9BE8",  # blue
    "#E8844C",  # orange
    "#4CE878",  # green
    "#E84C4C",  # red
    "#B04CE8",  # purple
    "#E8D44C",  # yellow
    "#4CE8D4",  # teal
    "#E84CB0",  # pink
]
BENCHMARK_COLOR = "#FFFFFF"
BG_DARK  = "#0D1117"
BG_PANEL = "#161B22"
GRID_COL = "#21262D"
TEXT_COL = "#E6EDF3"
SUBTEXT  = "#8B949E"

plt.rcParams.update({
    "figure.facecolor":  BG_DARK,
    "axes.facecolor":    BG_PANEL,
    "axes.edgecolor":    GRID_COL,
    "axes.labelcolor":   TEXT_COL,
    "axes.titlecolor":   TEXT_COL,
    "xtick.color":       SUBTEXT,
    "ytick.color":       SUBTEXT,
    "grid.color":        GRID_COL,
    "grid.linewidth":    0.5,
    "legend.facecolor":  BG_PANEL,
    "legend.edgecolor":  GRID_COL,
    "legend.labelcolor": TEXT_COL,
    "text.color":        TEXT_COL,
    "font.family":       "DejaVu Sans",
    "font.size":         10,
})

# ─── Helpers ──────────────────────────────────────────────────────────────────

def tryry(val, default=0.0):
    """Safely parse a percentage string like '2.28%' -> 2.28"""
    try:
        return float(str(val).replace("%", "").replace("∞", "inf").replace("-inf", "-999").replace("inf", "999"))
    except Exception:
        return default


def load_results(date_filter=None):
    """Load all timestamped (non-latest) result JSON files, optionally filtered by date tag."""
    pattern = os.path.join(RESULTS_DIR, "BIST30_*.json")
    files = sorted(glob.glob(pattern))
    results = []
    seen_aliases = {}

    for fpath in files:
        fname = os.path.basename(fpath)
        # Skip latest_* files
        if fname.startswith("latest_"):
            continue
        # Optional date filter (e.g. "20260602")
        if date_filter and date_filter not in fname:
            continue
        try:
            with open(fpath) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [WARN] Could not read {fname}: {e}")
            continue

        alias = data.get("alias", fname)
        # Skip excluded/broken models
        if alias in EXCLUDE_ALIASES or alias.split("/")[-1] in EXCLUDE_ALIASES:
            print(f"  [SKIP] Excluded alias '{alias}'")
            continue
        # If same alias already loaded, keep the newer file (by filename timestamp)
        if alias in seen_aliases:
            print(f"  [SKIP] Duplicate alias '{alias}' — keeping first loaded.")
            continue
        seen_aliases[alias] = True

        history  = data.get("history", [])
        bh       = data.get("benchmark", {}).get("history", [])
        metrics  = data.get("metrics", {})
        detailed = data.get("detailed_history", [])
        dr       = data.get("date_range", ["?", "?"])

        results.append({
            "alias":    alias,
            "history":  history,
            "benchmark":bh,
            "metrics":  metrics,
            "detailed": detailed,
            "date_range": dr,
            "approach": data.get("trading_approach", "Balanced"),
        })
        print(f"  [OK] Loaded: {alias}  ({dr[0]} → {dr[1]})  Return={metrics.get('Cumulative Return','?')}")
    return results


def make_dates(start_str, n):
    """Generate n business-day labels from start_str."""
    start = datetime.strptime(start_str, "%Y-%m-%d")
    dates = []
    d = start
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime("%d %b"))
        d += timedelta(days=1)
    return dates


def fmt_try(x, pos):
    return f"₺{x/1_000_000:.2f}M"


def fmt_pct(x, pos):
    return f"{x:.1f}%"

# ─── Plot 1: Portfolio Value Over Time ────────────────────────────────────────

def plot_portfolio_value(results, out_path):
    if not results:
        return

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_PANEL)

    initial = results[0]["history"][0] if results[0]["history"] else 1_000_000

    # Benchmark (first result's benchmark, they should share it)
    bh = results[0]["benchmark"]
    if bh:
        n = len(bh)
        xs = list(range(n))
        dates = make_dates(results[0]["date_range"][0], n)
        ax.plot(xs, bh, label="BIST30 Buy & Hold",
                color=BENCHMARK_COLOR, linewidth=1.8, linestyle="--", alpha=0.7)
        ax.fill_between(xs, bh, initial, color=BENCHMARK_COLOR, alpha=0.04)

    # Models
    for i, r in enumerate(results):
        h = r["history"]
        if not h:
            continue
        xs = list(range(len(h)))
        col = PALETTE[i % len(PALETTE)]
        label = r["alias"].split("/")[-1]  # shorten "google/gemini-2.5-pro" → "gemini-2.5-pro"
        ax.plot(xs, h, label=label, color=col, linewidth=2.2)
        ax.fill_between(xs, h, initial, color=col, alpha=0.06)

    # Reference line
    ax.axhline(y=initial, color=SUBTEXT, linewidth=0.8, linestyle=":", alpha=0.6)

    # X ticks — use dates
    n_ticks = len(results[0]["history"])
    dates = make_dates(results[0]["date_range"][0], n_ticks)
    step = max(1, n_ticks // 8)
    ax.set_xticks(range(0, n_ticks, step))
    ax.set_xticklabels(dates[::step], rotation=30, ha="right", fontsize=9)

    ax.yaxis.set_major_formatter(FuncFormatter(fmt_try))
    ax.set_title("BIST30 LLM Benchmark — Portfolio Value", fontsize=16, fontweight="bold", pad=16)
    ax.set_xlabel("Trading Day", fontsize=11)
    ax.set_ylabel("Portfolio Value (₺ TRY)", fontsize=11)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.8)
    ax.grid(True, linestyle="--", alpha=0.4)

    dr = results[0]["date_range"]
    fig.text(0.99, 0.01, f"Period: {dr[0]} → {dr[1]}  |  Strategy: Balanced Intraday Futures",
             ha="right", va="bottom", fontsize=8, color=SUBTEXT)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_DARK)
    plt.close()
    print(f"  → Saved: {out_path}")


# ─── Plot 2: Normalised Return (% vs initial) ─────────────────────────────────

def plot_normalized_return(results, out_path):
    if not results:
        return

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_PANEL)

    bh = results[0]["benchmark"]
    if bh and bh[0]:
        bh_pct = [(v / bh[0] - 1) * 100 for v in bh]
        ax.plot(bh_pct, label="BIST30 Buy & Hold",
                color=BENCHMARK_COLOR, linewidth=1.8, linestyle="--", alpha=0.7)
        ax.fill_between(range(len(bh_pct)), bh_pct, 0, color=BENCHMARK_COLOR, alpha=0.04)

    for i, r in enumerate(results):
        h = r["history"]
        if not h or h[0] == 0:
            continue
        pct = [(v / h[0] - 1) * 100 for v in h]
        col = PALETTE[i % len(PALETTE)]
        label = r["alias"].split("/")[-1]
        ax.plot(pct, label=label, color=col, linewidth=2.2)
        ax.fill_between(range(len(pct)), pct, 0, color=col, alpha=0.07)

    ax.axhline(y=0, color=SUBTEXT, linewidth=0.9, linestyle=":", alpha=0.7)

    n_ticks = len(results[0]["history"])
    dates = make_dates(results[0]["date_range"][0], n_ticks)
    step = max(1, n_ticks // 8)
    ax.set_xticks(range(0, n_ticks, step))
    ax.set_xticklabels(dates[::step], rotation=30, ha="right", fontsize=9)

    ax.yaxis.set_major_formatter(FuncFormatter(fmt_pct))
    ax.set_title("BIST30 LLM Benchmark — Normalised Return (%)", fontsize=16, fontweight="bold", pad=16)
    ax.set_xlabel("Trading Day", fontsize=11)
    ax.set_ylabel("Return vs. Initial Capital (%)", fontsize=11)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.8)
    ax.grid(True, linestyle="--", alpha=0.4)

    dr = results[0]["date_range"]
    fig.text(0.99, 0.01, f"Period: {dr[0]} → {dr[1]}",
             ha="right", va="bottom", fontsize=8, color=SUBTEXT)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_DARK)
    plt.close()
    print(f"  → Saved: {out_path}")


# ─── Plot 3: Metrics Comparison Bar Chart ─────────────────────────────────────

def plot_metrics_comparison(results, out_path):
    if not results:
        return

    metric_keys = ["Cumulative Return", "Max Drawdown", "Win Rate", "Sharpe Ratio", "Calmar Ratio"]
    metric_labels = ["Cum. Return (%)", "Max Drawdown (%)", "Win Rate (%)", "Sharpe Ratio", "Calmar Ratio"]

    # Parse metric values
    rows = []
    for r in results:
        m = r["metrics"]
        label = r["alias"].split("/")[-1]
        row = {"alias": label}
        row["Cumulative Return"] = tryry(m.get("Cumulative Return", "0%"))
        row["Max Drawdown"]      = tryry(m.get("Max Drawdown", "0%"))
        row["Win Rate"]          = tryry(m.get("Win Rate", "0%"))
        row["Sharpe Ratio"]      = tryry(m.get("Sharpe Ratio", "0"))
        row["Calmar Ratio"]      = tryry(m.get("Calmar Ratio", "0"))
        rows.append(row)

    if not rows:
        return

    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor(BG_DARK)
    gs = GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)
    axes = [
        fig.add_subplot(gs[0, 0]),
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[0, 2]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
    ]

    aliases = [r["alias"] for r in rows]
    short_aliases = [a.split("/")[-1][:20] for a in aliases]

    for ax_idx, (key, label) in enumerate(zip(metric_keys, metric_labels)):
        ax = axes[ax_idx]
        ax.set_facecolor(BG_PANEL)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_COL)

        vals = [r[key] for r in rows]
        colors = []
        for v in vals:
            if key == "Max Drawdown":
                colors.append("#E84C4C" if v < 0 else "#4CE878")
            elif key in ("Cumulative Return", "Win Rate", "Calmar Ratio"):
                colors.append("#4CE878" if v >= 0 else "#E84C4C")
            else:  # Sharpe
                colors.append("#4C9BE8" if v >= 0 else "#E84C4C")

        bars = ax.bar(range(len(vals)), vals, color=colors, width=0.55, zorder=3)

        # Value labels on bars
        for bar, v in zip(bars, vals):
            ypos = bar.get_height() + (max(abs(max(vals, default=0)), abs(min(vals, default=0))) * 0.03)
            if v < 0:
                ypos = bar.get_height() - (max(abs(max(vals, default=0)), abs(min(vals, default=0))) * 0.08)
            suffix = "%" if "%" in label or key in ("Cumulative Return", "Max Drawdown", "Win Rate") else ""
            ax.text(bar.get_x() + bar.get_width() / 2, ypos,
                    f"{v:.2f}{suffix}", ha="center", va="bottom",
                    fontsize=8.5, color=TEXT_COL, fontweight="bold")

        ax.set_xticks(range(len(short_aliases)))
        ax.set_xticklabels(short_aliases, rotation=25, ha="right", fontsize=8)
        ax.tick_params(colors=SUBTEXT)
        ax.set_title(label, fontsize=11, fontweight="bold", color=TEXT_COL, pad=8)
        ax.axhline(y=0, color=SUBTEXT, linewidth=0.8, linestyle="--", alpha=0.5)
        ax.grid(axis="y", color=GRID_COL, linewidth=0.5, linestyle="--", zorder=0)

    # Hide the 6th subplot
    fig.add_subplot(gs[1, 2]).set_visible(False)

    fig.suptitle("BIST30 LLM Benchmark — Performance Metrics", fontsize=17, fontweight="bold",
                 color=TEXT_COL, y=1.02)

    dr = results[0]["date_range"]
    fig.text(0.99, -0.02, f"Period: {dr[0]} → {dr[1]}  |  Exchange: BIST30  |  Strategy: Balanced",
             ha="right", va="bottom", fontsize=8, color=SUBTEXT)

    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_DARK)
    plt.close()
    print(f"  → Saved: {out_path}")


# ─── Plot 4: Daily Decision Heatmap ───────────────────────────────────────────

def plot_decision_heatmap(results, out_path):
    """Shows LONG/SHORT/FLAT/HOLD decision for each model per trading day."""
    if not results:
        return

    decision_map = {"LONG": 1, "SHORT": -1, "FLAT": 0, "HOLD": 0.5}
    color_map = {1: "#4CE878", -1: "#E84C4C", 0: "#8B949E", 0.5: "#E8D44C"}
    label_map = {1: "L", -1: "S", 0: "F", 0.5: "H"}

    max_days = max(len(r["detailed"]) for r in results)
    aliases  = [r["alias"].split("/")[-1][:22] for r in results]

    fig, ax = plt.subplots(figsize=(max(12, max_days * 1.2), max(4, len(results) * 0.8 + 2)))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_PANEL)

    for row_idx, r in enumerate(results):
        for col_idx, day in enumerate(r["detailed"]):
            dec = day.get("decision", "FLAT").upper()
            val = decision_map.get(dec, 0)
            col = color_map.get(val, "#8B949E")
            rect = plt.Rectangle([col_idx - 0.45, row_idx - 0.4], 0.9, 0.8,
                                  facecolor=col, edgecolor=BG_DARK, linewidth=1.5, zorder=3)
            ax.add_patch(rect)
            lbl = label_map.get(val, "?")
            conf = day.get("confidence", "")
            cell_text = f"{lbl}\n{conf}%" if conf != "" else lbl
            ax.text(col_idx, row_idx, cell_text, ha="center", va="center",
                    fontsize=7.5, color="black", fontweight="bold", zorder=4)

    ax.set_xlim(-0.6, max_days - 0.4)
    ax.set_ylim(-0.7, len(results) - 0.3)

    # Y ticks = model names
    ax.set_yticks(range(len(aliases)))
    ax.set_yticklabels(aliases, fontsize=9)

    # X ticks = dates
    if results[0]["detailed"]:
        day_labels = [d.get("date", str(i))[:5] for i, d in enumerate(results[0]["detailed"])]
        ax.set_xticks(range(len(day_labels)))
        ax.set_xticklabels(day_labels, rotation=35, ha="right", fontsize=8.5)

    ax.set_title("BIST30 LLM Benchmark — Daily Trading Decisions",
                 fontsize=15, fontweight="bold", color=TEXT_COL, pad=14)

    # Legend
    legend_patches = [
        mpatches.Patch(color="#4CE878", label="LONG"),
        mpatches.Patch(color="#E84C4C", label="SHORT"),
        mpatches.Patch(color="#8B949E", label="FLAT"),
        mpatches.Patch(color="#E8D44C", label="HOLD"),
    ]
    ax.legend(handles=legend_patches, loc="upper right", fontsize=9, framealpha=0.8)
    ax.grid(False)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_DARK)
    plt.close()
    print(f"  → Saved: {out_path}")


# ─── Plot 5: Drawdown Chart ───────────────────────────────────────────────────

def plot_drawdown(results, out_path):
    if not results:
        return

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_PANEL)

    for i, r in enumerate(results):
        h = r["history"]
        if not h:
            continue
        s = pd.Series(h)
        dd = (s / s.cummax() - 1) * 100
        col = PALETTE[i % len(PALETTE)]
        label = r["alias"].split("/")[-1]
        ax.plot(dd.values, label=label, color=col, linewidth=1.8)
        ax.fill_between(range(len(dd)), dd.values, 0, color=col, alpha=0.12)

    ax.axhline(y=0, color=SUBTEXT, linewidth=0.8, linestyle=":", alpha=0.6)

    n_ticks = len(results[0]["history"])
    dates = make_dates(results[0]["date_range"][0], n_ticks)
    step = max(1, n_ticks // 8)
    ax.set_xticks(range(0, n_ticks, step))
    ax.set_xticklabels(dates[::step], rotation=30, ha="right", fontsize=9)

    ax.yaxis.set_major_formatter(FuncFormatter(fmt_pct))
    ax.set_title("BIST30 LLM Benchmark — Drawdown (%)", fontsize=15, fontweight="bold", pad=14)
    ax.set_xlabel("Trading Day", fontsize=11)
    ax.set_ylabel("Drawdown from Peak (%)", fontsize=11)
    ax.legend(loc="lower left", fontsize=9, framealpha=0.8)
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_DARK)
    plt.close()
    print(f"  → Saved: {out_path}")


# ─── Plot 6: Result Card (App-style Leaderboard + Equity) ─────────────────────

def plot_result_card(results, out_path):
    """
    Flagship summary graphic mimicking the app's dashboard:
    - Top: Leaderboard table with rank, model, metrics, colour-coded
    - Bottom: Overlaid equity curves (area) with benchmark
    """
    if not results:
        return

    n = len(results)

    # Sort by cumulative return descending (best first)
    def cum_ret_val(r):
        return tryry(r["metrics"].get("Cumulative Return", "0%"))

    ranked = sorted(results, key=cum_ret_val, reverse=True)

    # ── Figure layout ──
    fig = plt.figure(figsize=(18, 14))
    fig.patch.set_facecolor(BG_DARK)

    # Top half: leaderboard table (60%), bottom half: equity chart (40%)
    gs = GridSpec(2, 1, figure=fig, height_ratios=[1.1, 1.4], hspace=0.08)
    ax_table = fig.add_subplot(gs[0])
    ax_chart = fig.add_subplot(gs[1])

    ax_table.set_facecolor(BG_DARK)
    ax_chart.set_facecolor(BG_PANEL)

    # ── Leaderboard Table ──
    ax_table.set_xlim(0, 1)
    ax_table.set_ylim(0, n + 1.5)
    ax_table.axis("off")

    # Header
    cols      = ["Rank", "Model", "Return", "Max DD", "Win Rate", "Sharpe", "Calmar", "Approach"]
    col_x     = [0.02, 0.10, 0.33, 0.44, 0.54, 0.64, 0.74, 0.84]
    col_align = ["center", "left", "right", "right", "right", "right", "right", "center"]

    # Header row bg
    header_rect = mpatches.FancyBboxPatch((0, n + 0.6), 1.0, 0.75,
                                          boxstyle="round,pad=0.01",
                                          linewidth=0, facecolor="#21262D")
    ax_table.add_patch(header_rect)

    for cx, label, align in zip(col_x, cols, col_align):
        ha = align
        ax_table.text(cx, n + 0.97, label.upper(),
                      ha=ha, va="center", fontsize=8.5,
                      color=SUBTEXT, fontweight="bold", fontfamily="monospace")

    # Separator line
    ax_table.axhline(y=n + 0.58, color=GRID_COL, linewidth=1.0, xmin=0, xmax=1)

    # Rows
    medal_colors = ["#FFD700", "#C0C0C0", "#CD7F32"]  # gold, silver, bronze

    for row_i, r in enumerate(ranked):
        rank    = row_i + 1
        y_pos   = n - row_i - 0.5
        m       = r["metrics"]
        alias   = r["alias"].split("/")[-1]
        color   = PALETTE[row_i % len(PALETTE)]

        cum_ret  = tryry(m.get("Cumulative Return", "0%"))
        max_dd   = tryry(m.get("Max Drawdown", "0%"))
        win_rate = tryry(m.get("Win Rate", "0%"))
        sharpe   = tryry(m.get("Sharpe Ratio", "0"))
        calmar   = tryry(m.get("Calmar Ratio", "0"))
        approach = r.get("approach", "Balanced")

        # Row background (alternating)
        bg_col = "#161B22" if row_i % 2 == 0 else "#0D1117"
        row_rect = mpatches.FancyBboxPatch((0, y_pos - 0.38), 1.0, 0.76,
                                           boxstyle="round,pad=0.005",
                                           linewidth=0, facecolor=bg_col)
        ax_table.add_patch(row_rect)

        # Coloured left bar
        bar_rect = mpatches.FancyBboxPatch((0, y_pos - 0.38), 0.004, 0.76,
                                           boxstyle="square,pad=0",
                                           linewidth=0, facecolor=color)
        ax_table.add_patch(bar_rect)

        # Rank medal / number
        medal_col = medal_colors[row_i] if rank <= 3 else SUBTEXT
        ax_table.text(col_x[0], y_pos, f"#{rank}",
                      ha="center", va="center", fontsize=11,
                      color=medal_col, fontweight="bold")

        # Model name
        ax_table.text(col_x[1], y_pos, alias,
                      ha="left", va="center", fontsize=9.5,
                      color=color, fontweight="bold")

        # Return — green/red
        ret_col = "#4CE878" if cum_ret >= 0 else "#E84C4C"
        ret_sign = "+" if cum_ret >= 0 else ""
        ax_table.text(col_x[2], y_pos, f"{ret_sign}{cum_ret:.2f}%",
                      ha="right", va="center", fontsize=9.5,
                      color=ret_col, fontweight="bold", fontfamily="monospace")

        # Max DD — always red
        ax_table.text(col_x[3], y_pos, f"{max_dd:.2f}%",
                      ha="right", va="center", fontsize=9,
                      color="#E84C4C", fontfamily="monospace")

        # Win Rate
        wr_col = "#4CE878" if win_rate >= 50 else "#E8D44C"
        ax_table.text(col_x[4], y_pos, f"{win_rate:.1f}%",
                      ha="right", va="center", fontsize=9,
                      color=wr_col, fontfamily="monospace")

        # Sharpe
        sh_col = "#4C9BE8" if sharpe >= 0 else "#E84C4C"
        ax_table.text(col_x[5], y_pos, f"{sharpe:.2f}",
                      ha="right", va="center", fontsize=9,
                      color=sh_col, fontfamily="monospace")

        # Calmar
        ca_col = "#4CE878" if calmar >= 0 else "#E84C4C"
        ax_table.text(col_x[6], y_pos, f"{calmar:.2f}",
                      ha="right", va="center", fontsize=9,
                      color=ca_col, fontfamily="monospace")

        # Approach badge
        ap_colors = {"Balanced": "#4C9BE8", "Aggressive": "#E84C4C", "Conservative": "#4CE878"}
        ap_col = ap_colors.get(approach, SUBTEXT)
        badge = mpatches.FancyBboxPatch((col_x[7] - 0.055, y_pos - 0.2), 0.115, 0.4,
                                        boxstyle="round,pad=0.01",
                                        linewidth=1, edgecolor=ap_col,
                                        facecolor=ap_col + "22")
        ax_table.add_patch(badge)
        ax_table.text(col_x[7], y_pos, approach,
                      ha="center", va="center", fontsize=7.5,
                      color=ap_col, fontweight="bold")

    # Title above table
    ax_table.text(0.5, n + 1.42,
                  "BIST30 LLM Benchmark — Model Leaderboard",
                  ha="center", va="center", fontsize=17, fontweight="bold",
                  color=TEXT_COL)

    dr = results[0]["date_range"]
    ax_table.text(0.5, n + 1.12,
                  f"Period: {dr[0]}  →  {dr[1]}   |   Exchange: BIST30   |   Strategy: Balanced Intraday Futures",
                  ha="center", va="center", fontsize=9, color=SUBTEXT)

    # ── Equity Curve (bottom) ──

    # Benchmark
    bh = results[0]["benchmark"]
    if bh and bh[0]:
        bh_pct = [(v / bh[0] - 1) * 100 for v in bh]
        xs = list(range(len(bh_pct)))
        ax_chart.plot(xs, bh_pct, color=BENCHMARK_COLOR, linewidth=1.6,
                      linestyle="--", alpha=0.6, label="BIST30 Buy & Hold", zorder=2)
        ax_chart.fill_between(xs, bh_pct, 0, color=BENCHMARK_COLOR, alpha=0.03)

    # Models — ranked order
    for i, r in enumerate(ranked):
        h = r["history"]
        if not h or h[0] == 0:
            continue
        pct = [(v / h[0] - 1) * 100 for v in h]
        col = PALETTE[i % len(PALETTE)]
        label = r["alias"].split("/")[-1]
        ax_chart.plot(pct, color=col, linewidth=2.2, label=label, zorder=3)
        ax_chart.fill_between(range(len(pct)), pct, 0, color=col, alpha=0.07)

    ax_chart.axhline(y=0, color=SUBTEXT, linewidth=0.8, linestyle=":", alpha=0.6)

    n_ticks = len(results[0]["history"])
    dates = make_dates(results[0]["date_range"][0], n_ticks)
    step = max(1, n_ticks // 8)
    ax_chart.set_xticks(range(0, n_ticks, step))
    ax_chart.set_xticklabels(dates[::step], rotation=25, ha="right", fontsize=9)
    ax_chart.yaxis.set_major_formatter(FuncFormatter(fmt_pct))
    ax_chart.set_ylabel("Return vs. Initial Capital (%)", fontsize=10, color=SUBTEXT)
    ax_chart.set_xlabel("Trading Day", fontsize=10, color=SUBTEXT)
    ax_chart.legend(loc="upper left", fontsize=8.5, framealpha=0.85,
                    ncol=min(n + 1, 4))
    ax_chart.grid(True, linestyle="--", alpha=0.3, color=GRID_COL)
    ax_chart.set_title("Comparative Equity Curves (Normalised %)",
                       fontsize=12, color=TEXT_COL, pad=10, fontweight="bold")

    for spine in ax_chart.spines.values():
        spine.set_edgecolor(GRID_COL)

    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_DARK)
    plt.close()
    print(f"  → Saved: {out_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Only use the recent (June 2026) runs
    date_filter = "20260602"

    print(f"\n{'='*60}")
    print(f"  BIST30 Plot Generator")
    print(f"  Filter: {date_filter}")
    print(f"  Output: {OUT_DIR}")
    print(f"{'='*60}\n")
    print("Loading results...")
    results = load_results(date_filter=date_filter)

    if not results:
        print("[ERROR] No results found. Run backtests first.")
        sys.exit(1)

    print(f"\nLoaded {len(results)} model(s). Generating plots...\n")

    plot_portfolio_value(results,     os.path.join(OUT_DIR, "01_portfolio_value.png"))
    plot_normalized_return(results,   os.path.join(OUT_DIR, "02_normalized_return.png"))
    plot_metrics_comparison(results,  os.path.join(OUT_DIR, "03_metrics_comparison.png"))
    plot_decision_heatmap(results,    os.path.join(OUT_DIR, "04_decision_heatmap.png"))
    plot_drawdown(results,            os.path.join(OUT_DIR, "05_drawdown.png"))
    plot_result_card(results,         os.path.join(OUT_DIR, "00_result_card.png"))

    print(f"\n✅ Done! {len(results)} models plotted → {OUT_DIR}")
