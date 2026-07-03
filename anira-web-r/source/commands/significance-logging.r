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
print(anova_rq12_result)

significant_rq12     <- anova_rq12_result[anova_rq12_result$`Pr(>F)` <  0.05, ]
non_significant_rq12 <- anova_rq12_result[anova_rq12_result$`Pr(>F)` >= 0.05, ]
message(paste("Significant (p < 0.05):",     nrow(significant_rq12)))
message(paste("Non-significant (p >= 0.05):", nrow(non_significant_rq12)))
print(significant_rq12)
print(non_significant_rq12)

message("")
message("--- For RQ3 ---")
message("")
anova_rq3_result <- readRDS(file.path(results_dir, "anova_rq3.rds"))
print(anova_rq3_result)

significant_rq3     <- anova_rq3_result[anova_rq3_result$`Pr(>F)` <  0.05, ]
non_significant_rq3 <- anova_rq3_result[anova_rq3_result$`Pr(>F)` >= 0.05, ]
message(paste("Significant (p < 0.05):",     nrow(significant_rq3)))
message(paste("Non-significant (p >= 0.05):", nrow(non_significant_rq3)))
print(significant_rq3)
print(non_significant_rq3)

source(here("source", "commands", "cleanup.r"))
q("no", save = "no")
