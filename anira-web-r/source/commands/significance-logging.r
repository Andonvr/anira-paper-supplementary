# The previous steps use an outdated significance threshold.
# Rather than recomputing all models, just to fix the logging,
# we just load the data once more and do final logging using the proper significance threshold.

library(here)
library(tidyverse)
library(lme4)
library(lmerTest)
library(performance)
library(parameters)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Exactly 1 argument must be supplied: <results_dir>")

results_dir <- args[1]

message("")
message("--- For RQ12 ---")
message("")
anova_rq12_result <- readRDS(file.path(results_dir, "anova_rq12.rds"))
# print(anova_rq12_result)

significant_rq12     <- anova_rq12_result[anova_rq12_result$`Pr(>F)` <  0.001, ]
non_significant_rq12 <- anova_rq12_result[anova_rq12_result$`Pr(>F)` >= 0.001, ]
message(paste("Significant (p < 0.001):",     nrow(significant_rq12)))
message(paste("Non-significant (p >= 0.001):", nrow(non_significant_rq12)))
print(significant_rq12)
print(non_significant_rq12)

message("")
message("--- For RQ3 ---")
message("")
anova_rq3_result <- readRDS(file.path(results_dir, "anova_rq3.rds"))
# print(anova_rq3_result)

significant_rq3     <- anova_rq3_result[anova_rq3_result$`Pr(>F)` <  0.001, ]
non_significant_rq3 <- anova_rq3_result[anova_rq3_result$`Pr(>F)` >= 0.001, ]
message(paste("Significant (p < 0.001):",     nrow(significant_rq3)))
message(paste("Non-significant (p >= 0.001):", nrow(non_significant_rq3)))
print(significant_rq3)
print(non_significant_rq3)

message("")
message("--- Threshold audit ---")
message("")
message("This log is the authoritative significance report (alpha = 0.001).")
message("Threshold-dependent text in earlier logs is superseded by this log:")
message("  - model-rq12.log / model-rq3.log: term counts split at p < 0.0001")
message("  - posthoc-rq3.log: Backend:PP interaction gate evaluated at p < 0.05")
message("Those thresholds affect log text only; all computed artifacts")
message("(models, EMMs, contrasts) are threshold-free and remain valid.")
message("")

# Re-evaluate the one threshold-dependent analysis decision at alpha = 0.001:
# posthoc-rq3.r averages over the other factor only if Backend:PP is non-significant.
backend_pp_p <- anova_rq3_result["Backend:PP", "Pr(>F)"]
message(sprintf(
  "Backend:PP interaction at alpha = 0.001: p = %.4g — %s",
  backend_pp_p,
  ifelse(backend_pp_p < 0.001,
         "SIGNIFICANT: averaging over the other factor may be misleading; use the per-level (simple-effects) contrasts",
         "non-significant: averaging over the other factor is justified")
))

source(here("source", "commands", "cleanup.r"))
q("no", save = "no")
