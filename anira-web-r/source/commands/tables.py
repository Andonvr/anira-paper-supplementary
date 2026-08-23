import csv
import math
import os
import re
import sys
from collections import defaultdict

ENV_ORDER = ["Native", "Chrome", "Firefox", "Safari"]

MODEL_ORDER = ["steerable-nafx", "guitar-lstm"]
MODEL_DISPLAY = {
    "steerable-nafx": "SteerableNAFX",
    "guitar-lstm": "GuitarLSTM",
}


def write_str_to_file(content: str, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)


# ── number formatting ──────────────────────────────────────────────────────────


def fmt_fixed(val: float) -> str:
    """Fixed-point with 3 significant digits for use in the runtime table."""
    if val == 0:
        return "$0$"
    exp = math.floor(math.log10(abs(val)))
    decimals = max(0, 2 - exp)
    return f"${val:.{decimals}f}$"


def fmt_ns(ns: int, fixed_decimal: bool = False) -> str:
    """Human-readable duration for the timer-resolution table.

    < 1000 ns  → 'X\\,ns'
    >= 1000 ns → 'X\\,$\\mu$s'  (whole number) or 'X.X\\,$\\mu$s' (fractional)

    Pass fixed_decimal=True to always show one decimal place (useful for
    columns that mix whole and fractional µs values).
    """
    if ns < 1000:
        return f"{ns}\\,ns"
    us = ns / 1000
    if fixed_decimal or us != int(us):
        return f"{us:.1f}\\,$\\mu$s"
    return f"{int(us)}\\,$\\mu$s"


# ── runtime (describe.csv) table ───────────────────────────────────────────────


def format_runtime_table(results_dir: str) -> str:
    csv_path = os.path.join(results_dir, "describe.csv")

    data: dict[str, dict] = defaultdict(dict)
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            data[row["Environment"]][row["Model"]] = (
                float(row["Mean"]),
                float(row["SE"]),
                float(row["CI_Lower"]),
                float(row["CI_Upper"]),
            )

    rows: list[str] = []
    for i, env in enumerate(ENV_ORDER):
        if env not in data:
            continue
        if i > 0:
            rows.append("\\midrule")
        models_present = [m for m in MODEL_ORDER if m in data[env]]
        n = len(models_present)
        for j, model in enumerate(models_present):
            mean, se, ci_lo, ci_hi = data[env][model]
            # describe.csv holds ms/sample; the paper reports µs/sample.
            mean_us, se_us = mean * 1e3, se * 1e3
            env_cell = f"\\multirow{{{n}}}{{*}}{{\\textbf{{{env}}}}}" if j == 0 else ""
            rows.append(
                f"  {env_cell} & {MODEL_DISPLAY[model]}"
                f" & {fmt_fixed(mean_us)} & {fmt_fixed(se_us)} \\\\"
            )

    body = "\n".join(rows)
    return (
        "\\begin{table}[htbp]\n"
        "\\caption{Descriptive statistics of \\emph{RpS} observations for the Bypass-Engine"
        " across different models and execution environments."
        " All values are expressed in $\\mu$s/sample.}\n"
        "\\label{tab:runtime-overview}\n"
        "\\centering\n"
        "\\setlength{\\tabcolsep}{3pt}\n"
        "\\begin{tabular}{llcc}\n"
        "\\toprule\n"
        "& \\textbf{Model} & \\textbf{Mean} & \\textbf{SE} \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\end{table}\n"
    )


# ── tail statistics (tails.csv) table ─────────────────────────────────────────


def fmt_pct(frac: float) -> str:
    pct = frac * 100
    if pct == 0:
        return "$0$"
    if pct == int(pct):
        return f"${int(pct)}$"
    return f"${pct:.1f}$"


def format_tail_table(results_dir: str, run: str = "onnx") -> str:
    """Tail statistics of RpS for one run (default: the bundled ONNX Runtime
    backend with the C++ pre/post-processor), by environment, model, and
    buffer size. Steady-state columns exclude iteration 0 of every repetition."""
    csv_path = os.path.join(results_dir, "tails.csv")

    data: dict[str, dict[str, dict[int, dict]]] = defaultdict(lambda: defaultdict(dict))
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["Run"] != run:
                continue
            data[row["Environment"]][row["Model"]][int(row["Buffer.Size"])] = row

    rows: list[str] = []
    for i, env in enumerate(ENV_ORDER):
        if env not in data:
            continue
        if i > 0:
            rows.append("\\midrule")
        models_present = [m for m in MODEL_ORDER if m in data[env]]
        n_env = sum(len(data[env][m]) for m in models_present)
        first_env_row = True
        for model in models_present:
            sizes = sorted(data[env][model])
            for j, bs in enumerate(sizes):
                r = data[env][model][bs]
                us = lambda key: fmt_fixed(float(r[key]) * 1e3)  # ms/sample -> µs/sample
                env_cell = f"\\multirow{{{n_env}}}{{*}}{{\\textbf{{{env}}}}}" if first_env_row else ""
                model_cell = f"\\multirow{{{len(sizes)}}}{{*}}{{{MODEL_DISPLAY[model]}}}" if j == 0 else ""
                first_env_row = False
                rows.append(
                    f"  {env_cell} & {model_cell} & {bs}"
                    f" & {us('SD')} & {us('P99')} & {us('Max')} & {us('Max_Steady')}"
                    f" & {fmt_pct(float(r['Miss']))} & {fmt_pct(float(r['Miss_Steady']))} \\\\"
                )

    body = "\n".join(rows)
    return (
        "\\begin{table}[htbp]\n"
        "\\caption{Tail statistics of \\emph{RpS} for the ONNX Runtime \\emph{backend}"
        " by \\emph{environment}, \\emph{model}, and \\emph{buffer size} (BS),"
        " over all 500 measurements of a run. SD, p99, and Max in $\\mu$s/sample"
        " (\\emph{RTT}~$\\approx$~22.68); Miss is the share of blocks exceeding the \\emph{RTT}."
        " Starred columns exclude \\emph{iteration}~0 of every \\emph{repetition}.}\n"
        "\\label{tab:tails}\n"
        "\\centering\n"
        "\\setlength{\\tabcolsep}{2pt}\n"
        "\\begin{tabular}{llrrrrrrr}\n"
        "\\toprule\n"
        "& \\textbf{Model} & \\textbf{BS} & \\textbf{SD} & \\textbf{p99} & \\textbf{Max}"
        " & \\textbf{Max*} & \\textbf{Miss} & \\textbf{Miss*} \\\\\n"
        "& & & & & & & \\textbf{(\\%)} & \\textbf{(\\%)} \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\end{table}\n"
    )


# ── timer resolution table ─────────────────────────────────────────────────────

_RE_RESOLUTION = re.compile(r"Timer resolution:\s+(\d+)\s+ns")


def parse_timer_log(log_path: str) -> int | None:
    """Return resolution_ns from a benchmark log file, or None."""
    text = open(log_path).read()
    m_res = _RE_RESOLUTION.search(text)
    if not m_res:
        return None
    return int(m_res.group(1))


def format_timer_resolution_table(log_dir: str) -> str:
    rows: list[str] = []
    for env in ENV_ORDER:
        log_path = os.path.join(log_dir, f"{env}.log")
        if not os.path.exists(log_path):
            continue
        res_ns = parse_timer_log(log_path)
        if res_ns is None:
            continue
        rows.append(f"{env} & {fmt_ns(res_ns)} \\\\")

    body = "\n".join(rows)
    return (
        "\\begin{table}[t]\n"
        "\\caption{\\texttt{steady\\_clock} timer resolution per platform,\n"
        "         measured on the benchmark machine.}\n"
        "\\label{tab:timer-resolution}\n"
        "\\centering\n"
        "\\begin{tabular}{lr}\n"
        "\\hline\n"
        "\\textbf{Platform} & \\textbf{Timer resolution} \\\\\n"
        "\\hline\n"
        f"{body}\n"
        "\\hline\n"
        "\\end{tabular}\n"
        "\\end{table}\n"
    )


def find_paper_figures(web_r_root: str) -> str | None:
    """Locate anira-paper-latex/figures next to anira-web-r, or one level up
    (anira-web-r lives inside anira-paper-supplementary/ in the monorepo).
    Returns None if absent, e.g. in a standalone supplementary checkout."""
    parent = os.path.dirname(web_r_root)
    for root in (parent, os.path.dirname(parent)):
        candidate = os.path.join(root, "anira-paper-latex", "figures")
        if os.path.isdir(candidate):
            return candidate
    return None


# ── main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tables.py <results_dir>")
        sys.exit(1)

    results_dir = sys.argv[1]
    out_dir = os.path.join(results_dir, "out")
    os.makedirs(out_dir, exist_ok=True)

    # Derive sibling directories from the results_dir path.
    web_r_root = os.path.dirname(os.path.dirname(os.path.abspath(results_dir)))
    monorepo_root = os.path.dirname(web_r_root)
    log_dir = os.path.join(web_r_root, "benchmark_logs")
    paper_figures = find_paper_figures(web_r_root)

    tables = {
        "runtime_table.tex": format_runtime_table(results_dir),
        "tail_table.tex": format_tail_table(results_dir),
        "timer_resolution.tex": format_timer_resolution_table(log_dir),
    }
    for name, tex in tables.items():
        write_str_to_file(tex, os.path.join(out_dir, name))
        if paper_figures:
            write_str_to_file(tex, os.path.join(paper_figures, name))
        print(f"{name} written" + (" (mirrored to paper figures)" if paper_figures else ""))
