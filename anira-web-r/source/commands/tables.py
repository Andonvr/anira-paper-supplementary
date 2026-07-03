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
    "guitar-lstm":    "GuitarLSTM",
}


def write_str_to_file(content: str, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)


# ── number formatting ──────────────────────────────────────────────────────────

def fmt_sci(val: float) -> str:
    """$X.XX\\cdot10^{Y}$ for use in the runtime table."""
    if val == 0:
        return "$0$"
    exp = math.floor(math.log10(abs(val)))
    mantissa = val / (10 ** exp)
    return f"${mantissa:.2f}\\cdot10^{{{exp}}}$"


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
            env_cell = f"\\multirow{{{n}}}{{*}}{{\\textbf{{{env}}}}}" if j == 0 else ""
            rows.append(
                f"  {env_cell} & {MODEL_DISPLAY[model]}"
                f" & {fmt_sci(mean)} & {fmt_sci(se)} \\\\"
            )

    body = "\n".join(rows)
    return (
        "\\begin{table}[htbp]\n"
        "\\caption{Descriptive statistics of \\emph{RpS} observations for the Bypass-Engine"
        " across different models and execution environments."
        " All values are expressed in milliseconds per sample.}\n"
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
        "\\caption{Measured \\texttt{steady\\_clock} timer resolution per platform,\n"
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


# ── main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tables.py <results_dir>")
        sys.exit(1)

    results_dir = sys.argv[1]
    out_dir = os.path.join(results_dir, "out")
    os.makedirs(out_dir, exist_ok=True)

    # Derive sibling directories from the results_dir path.
    web_r_root    = os.path.dirname(os.path.dirname(os.path.abspath(results_dir)))
    monorepo_root = os.path.dirname(web_r_root)
    log_dir       = os.path.join(web_r_root, "benchmark_logs")
    paper_figures = os.path.join(monorepo_root, "anira-paper-latex", "figures")

    # Runtime table → results out + paper figures
    runtime_tex = format_runtime_table(results_dir)
    write_str_to_file(runtime_tex, os.path.join(out_dir, "runtime_table.tex"))
    write_str_to_file(runtime_tex, os.path.join(paper_figures, "runtime_table.tex"))
    print(f"runtime_table.tex written")

    # Timer resolution table → results out + paper figures
    timer_tex = format_timer_resolution_table(log_dir)
    write_str_to_file(timer_tex, os.path.join(out_dir, "timer_resolution.tex"))
    write_str_to_file(timer_tex, os.path.join(paper_figures, "timer_resolution.tex"))
    print(f"timer_resolution.tex written")
