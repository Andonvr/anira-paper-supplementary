# Anira Web Statistics

Statistical analysis of the anira-web benchmarks: ingesting per-browser benchmark
logs, fitting mixed-effects models, running post-hoc tests, and producing the
tables and plots used in the paper.

## Setup

- Spin up the Docker container using the provided `Dockerfile_r-base` (or set up
  your own environment -- see `source/requirements.txt` and
  `source/install_packages.r`):
  ```
  docker build -f Dockerfile_r-base -t my-r-image .
  docker run --rm -v "$PWD":/home/ -w /home/ my-r-image <command>
  ```
- Place the benchmark logs in the `benchmark_logs/` directory (one `*.log` file
  per environment, e.g. `Native.log`, `Chrome.log`, `Firefox.log`,
  `Safari.log`), or use the ones provided.

## Usage

Everything runs through `run_advanced.sh`:

```
./run_advanced.sh <num_iterations> <nth_iterations> <step>
```

- **`num_iterations`** -- maximum number of iterations to consider.
- **`nth_iterations`** -- take every nth iteration. E.g. `./run_advanced.sh 25 5 all`
  uses the first 25 iterations, considering every 5th. Useful for quick runs
  without processing the whole dataset.
- **`step`** -- which stage of the pipeline to run (see below), or `all` to run
  every stage in sequence.

Outputs are written to `results/<num_iterations>-<nth_iterations>/`, with run
logs under `logs/` and generated artifacts (plots, `.tex` tables) under `out/`.

Example:

```
./run_advanced.sh 50 1 all
```

### Steps

Run in this order (or use `all`):

- **`ingest`** -- parses the `benchmark_logs/*.log` files into
  `benchmark_logs/raw.csv`.
- **`prepare`** -- filters the data, sets factor levels, applies the iteration
  window, and writes the per-RQ datasets (`data_rq12.rds`, `data_rq3.rds`).
- **`describe`** -- computes descriptive statistics (`describe.csv`).
- **`model-rq12`** -- fits the mixed-effects model for RQ1 (platform overhead)
  and RQ2 (cold-start) and runs the ANOVA.
- **`model-rq3`** -- fits the factorial (backend × pre/post-processing)
  mixed-effects model for RQ3 (JS component overhead) and runs the ANOVA.
- **`posthoc-rq12`** -- estimated marginal means and post-hoc contrasts for
  RQ1/RQ2.
- **`posthoc-rq3`** -- estimated marginal means and post-hoc contrasts for RQ3.
- **`significance-logging`** -- re-emits the significance results using the final
  significance threshold (without refitting the models).
- **`tables`** -- generates the LaTeX tables (`runtime_table.tex`,
  `timer_resolution.tex`).
- **`plots`** -- generates the figures (`rq1_environment.png`,
  `rq2_iteration_effects.png`, `rq3_overhead.png`).
- **`all`** -- runs every step above in sequence.

### Significance threshold

The final significance threshold used in the paper is **alpha = 0.001**. Some
earlier pipeline steps hardcode outdated thresholds in their _logging_:
`model-rq12` and `model-rq3` count significant ANOVA terms at `p < 0.0001`, and
`posthoc-rq3` reports the Backend:PP interaction gate at `p < 0.05`. These
thresholds only affect the text printed to the respective `logs/*.log` files --
none of the computed artifacts (fitted models, ANOVA tables, estimated marginal
means, contrasts) depend on a threshold, so they remain valid as-is and the
scripts do not need to be rerun. The **`significance-logging`** step is the
authoritative significance report: it re-reads the stored ANOVA results and
re-emits all threshold-dependent statements at alpha = 0.001, including the
Backend:PP interaction check.
This approach was taken as to not have to rerun a whole computationally heavy pipeline.
