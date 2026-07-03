import os
import sys

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

SIGNIFICANCE_THRESHOLD = 0.05

ENV_ORDER = ["Native", "Chrome", "Firefox", "Safari"]
ENV_COLORS = {
    "Native": "#66c2a5",
    "Chrome": "#e2e067",
    "Firefox": "#fc8d62",
    "Safari": "#8a96e7",
}

MODEL_ORDER = ["steerable-nafx", "guitar-lstm"]
MODEL_TITLES = {"steerable-nafx": "SteerableNAFX", "guitar-lstm": "GuitarLSTM"}
MODEL_COLORS = {"steerable-nafx": "#4A5AC6", "guitar-lstm": "#e07b39"}

BACKEND_LABELS = {
    "wasm-bypass": "WASM Bypass",
    "wasm-onnx": "WASM ONNX",
    "js-bypass": "JS Bypass",
    "js-onnx": "JS ONNX",
}
BACKEND_COLORS = {
    "wasm-bypass": "#66c2a5",
    "wasm-onnx": "#3288bd",
    "js-bypass": "#f46d43",
    "js-onnx": "#d53e4f",
}
PP_HATCHES = {"wasm": "", "js": "///"}

Y_LABEL = "Est. Means (µs / sample)"


def _apply_style():
    plt.rcParams.update(
        {
            "font.size": 12,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelsize": 13,
            "axes.titlesize": 14,
            "axes.grid": False,
            "legend.frameon": False,
        }
    )


def _load(results_dir, filename, label):
    path = os.path.join(results_dir, filename)
    if not os.path.exists(path):
        print(f"⚠️  Skipping {label} ({filename} not found)")
        return None
    return pd.read_csv(path)


def _save(fig, out_dir, filename):
    path = os.path.join(out_dir, filename)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ Saved {path}")


# ---------------------------------------------------------------------------
# RQ1 & RQ2 plots (LMM-I: environment + iteration effects)
# ---------------------------------------------------------------------------


def plot_rq1_environment(results_dir, out_dir):
    """Bar chart: geometric mean EMMs by environment, rows = model, cols = run."""
    df = _load(results_dir, "emm_rq1_environment.csv", "RQ1 environment")
    if df is None:
        return

    _apply_style()
    plt.rcParams.update({"font.size": 14, "axes.labelsize": 15, "xtick.labelsize": 13})

    df["Environment"] = pd.Categorical(
        df["Environment"], categories=ENV_ORDER, ordered=True
    )
    envs = [e for e in ENV_ORDER if e in df["Environment"].unique()]
    models = [m for m in MODEL_ORDER if m in df["Model.Unique"].unique()]
    x = np.arange(len(envs))
    colors = [ENV_COLORS.get(e, "#cccccc") for e in envs]

    run_titles = {"bypass": "Bypass", "onnx": "ONNX"}
    n_rows, n_cols = len(models), len(run_titles)

    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(5 * n_cols, 3.6 * n_rows),
        squeeze=False,
        constrained_layout=True,
    )

    for row_idx, model in enumerate(models):
        for col_idx, (run, title) in enumerate(run_titles.items()):
            ax = axes[row_idx][col_idx]
            rows = (
                df[(df["Run"] == run) & (df["Model.Unique"] == model)]
                .set_index("Environment")
                .reindex(envs)
            )
            y = rows["response"].values * 1e3
            lo = rows["lower.CL"].values * 1e3
            hi = rows["upper.CL"].values * 1e3

            ax.bar(
                x,
                y,
                width=0.7,
                yerr=[y - lo, hi - y],
                color=colors,
                capsize=3,
                alpha=0.9,
                edgecolor="black",
                linewidth=0.5,
            )
            ax.set_xticks(x)
            ax.set_xticklabels(envs, rotation=45, ha="right")
            letter = chr(97 + row_idx * n_cols + col_idx)
            ax.text(
                0.03, 0.97, f"{letter})", transform=ax.transAxes, va="top", fontsize=12
            )
            if row_idx == 0:
                ax.set_title(title, fontweight="bold")
            if col_idx == 0:
                ax.set_ylabel(
                    MODEL_TITLES.get(model, model), fontweight="bold", fontsize=13
                )

    fig.supylabel(Y_LABEL)
    _save(fig, out_dir, "rq1_environment.png")


def plot_rq2_iterations(results_dir, out_dir):
    """Line plot: warm-up effects across iterations, ONNX run only, one row per environment."""
    df = _load(results_dir, "emm_rq2_iterations.csv", "RQ2 iterations")
    if df is None:
        return

    _apply_style()

    df["significant"] = df["p.value"] < SIGNIFICANCE_THRESHOLD
    df["Environment"] = pd.Categorical(
        df["Environment"], categories=ENV_ORDER, ordered=True
    )

    onnx = df[df["Run"] == "onnx"]
    envs = [e for e in ENV_ORDER if e in onnx["Environment"].unique()]
    models = [m for m in MODEL_ORDER if m in onnx["Model.Unique"].unique()]

    fig, axes = plt.subplots(len(envs), 1, figsize=(7.5, 2 * len(envs)), sharex=True)
    if len(envs) == 1:
        axes = [axes]

    for ax, env in zip(axes, envs):
        for model in models:
            color = MODEL_COLORS.get(model, "#cccccc")
            darker = tuple(c * 0.8 for c in mcolors.to_rgb(color))
            d = onnx[
                (onnx["Environment"] == env) & (onnx["Model.Unique"] == model)
            ].sort_values("Iteration")
            if d.empty:
                continue
            x = d["Iteration"].values
            y = d["response"].values * 1e3
            ax.plot(x, y, "-", lw=1, color=color)
            ax.fill_between(
                x,
                d["lower.CL"].values * 1e3,
                d["upper.CL"].values * 1e3,
                color=color,
                alpha=0.15,
            )
            ax.scatter(x, y, s=25, color=color, zorder=3)
            ax.axhline(y.mean(), ls="--", color=color, lw=1, alpha=0.7)
            sig = d[d["significant"]]
            if not sig.empty:
                ax.scatter(
                    sig["Iteration"].values,
                    sig["response"].values * 1e3,
                    marker="*",
                    s=50,
                    color=darker,
                    zorder=5,
                )

        ax.set_title(env, loc="left", fontweight="bold")

    axes[-1].set_xlabel("Iteration")

    solid_handles = []
    avg_handles = []
    for m in models:
        c = MODEL_COLORS.get(m, "#cccccc")
        t = MODEL_TITLES.get(m, m)
        solid_handles.append(Line2D([0], [0], color=c, lw=2, label=t))
        avg_handles.append(
            Line2D([0], [0], color=c, lw=1.5, ls="--", alpha=0.7, label=f"{t} avg")
        )
    star_handle = Line2D(
        [0], [0], marker="*", color="black", lw=0, label=f'p < {SIGNIFICANCE_THRESHOLD} vs. grand mean'
    )
    legend_handles = solid_handles + [star_handle] + avg_handles
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=len(models) + 1,
        bbox_to_anchor=(0.5, -0.05),
        frameon=True,
    )
    fig.supylabel(Y_LABEL, x=0.02)
    fig.subplots_adjust(top=0.97, bottom=0.1, hspace=0.25)
    _save(fig, out_dir, "rq2_iteration_effects.png")


# ---------------------------------------------------------------------------
# RQ3 plot
# ---------------------------------------------------------------------------


def plot_rq3_overhead(results_dir, out_dir):
    """Single wide figure: rows=browsers, cols=model×backend_group, legend at bottom."""
    df = _load(results_dir, "emm_rq3_factorial.csv", "RQ3 overhead")
    if df is None:
        return

    _apply_style()
    plt.rcParams.update({"font.size": 11, "axes.labelsize": 12, "xtick.labelsize": 10})

    df["Buffer.Size"] = pd.to_numeric(df["Buffer.Size"]).astype(int)
    df["Environment"] = pd.Categorical(
        df["Environment"], categories=ENV_ORDER, ordered=True
    )

    web_envs = [
        e for e in ENV_ORDER if e != "Native" and e in df["Environment"].unique()
    ]
    models = [m for m in MODEL_ORDER if m in df["Model.Unique"].unique()]
    buf_sizes = sorted(df["Buffer.Size"].unique())
    x = np.arange(len(buf_sizes))

    backend_groups = [
        ("bypass", "Bypass", ["wasm-bypass", "js-bypass"]),
        ("onnx", "ONNX", ["wasm-onnx", "js-onnx"]),
    ]
    pp_order = ["wasm", "js"]

    n_plot_cols = len(models) * len(backend_groups)  # 4
    n_rows = len(web_envs)

    fig = plt.figure(figsize=(4.5 * n_plot_cols, 3 * n_rows))
    gs = GridSpec(n_rows, n_plot_cols, figure=fig, hspace=0.2, wspace=0.3)

    global_col = 0
    for group_key, group_title, backends in backend_groups:
        combos = [(b, pp) for b in backends for pp in pp_order]
        bar_width = 0.88 / len(combos)
        offsets = np.linspace(-0.44 + bar_width / 2, 0.44 - bar_width / 2, len(combos))

        for model in models:
            for row_idx, env in enumerate(web_envs):
                ax = fig.add_subplot(gs[row_idx, global_col])
                sub = df[(df["Environment"] == env) & (df["Model.Unique"] == model)]

                for i, (backend, pp) in enumerate(combos):
                    bdata = (
                        sub[(sub["Backend"] == backend) & (sub["PP"] == pp)]
                        .set_index("Buffer.Size")
                        .reindex(buf_sizes)
                    )
                    if bdata.isna().values.any():
                        continue
                    y = bdata["response"].values * 1e3
                    lo = bdata["lower.CL"].values * 1e3
                    hi = bdata["upper.CL"].values * 1e3
                    ax.bar(
                        x + offsets[i],
                        y,
                        width=bar_width,
                        yerr=[y - lo, hi - y],
                        color=BACKEND_COLORS[backend],
                        hatch=PP_HATCHES[pp],
                        capsize=2,
                        alpha=0.9,
                        edgecolor="black",
                        linewidth=0.5,
                    )

                letter = chr(97 + row_idx * n_plot_cols + global_col)
                ax.text(
                    0.03,
                    0.97,
                    f"{letter})",
                    transform=ax.transAxes,
                    va="top",
                    fontsize=10,
                )

                if row_idx == 0:
                    ax.set_title(
                        f"{group_title}\n{MODEL_TITLES.get(model, model)}",
                        fontweight="bold",
                        fontsize=12,
                    )
                if global_col == 0:
                    ax.set_ylabel(env, fontweight="bold", fontsize=12)

                ax.set_xticks(x)
                ax.set_xticklabels([str(bs) for bs in buf_sizes], fontsize=9)
                ax.set_yscale("log")
                ax.yaxis.set_major_locator(
                    ticker.LogLocator(base=10, subs=[1, 2, 3, 5])
                )
                ax.yaxis.set_major_formatter(
                    ticker.LogFormatterSciNotation(labelOnlyBase=False)
                )
                ax.yaxis.set_minor_formatter(ticker.NullFormatter())

            global_col += 1

    all_backends = [b for _, _, bs in backend_groups for b in bs]
    backend_handles = [
        Patch(
            facecolor=BACKEND_COLORS[b],
            edgecolor="black",
            lw=0.5,
            label=BACKEND_LABELS[b],
        )
        for b in all_backends
    ]
    pp_handles = [
        Patch(
            facecolor="#aaaaaa",
            hatch=PP_HATCHES[pp],
            edgecolor="black",
            lw=0.5,
            label=f"{'WASM' if pp == 'wasm' else 'JS'} PP",
        )
        for pp in pp_order
    ]
    fig.legend(
        handles=backend_handles + pp_handles,
        loc="lower center",
        ncol=len(backend_handles) + len(pp_handles),
        bbox_to_anchor=(0.5, -0.01),
        frameon=True,
        fontsize=11,
    )
    plt.subplots_adjust(bottom=0.06)

    _save(fig, out_dir, "rq3_overhead.png")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plots.py <results_dir>")
        sys.exit(1)

    results_dir = sys.argv[1]
    out_dir = os.path.join(results_dir, "out")
    os.makedirs(out_dir, exist_ok=True)

    plot_rq1_environment(results_dir, out_dir)
    plot_rq2_iterations(results_dir, out_dir)
    plot_rq3_overhead(results_dir, out_dir)
