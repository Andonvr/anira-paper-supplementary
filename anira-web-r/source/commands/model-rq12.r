library(here)
library(tidyverse)
library(lme4)
library(lmerTest)
library(performance)
library(parameters)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Exactly 1 argument must be supplied: <results_dir>")

results_dir <- args[1]
data <- readRDS(file.path(results_dir, "data_rq12.rds"))

# LMM-I for RQ1 (platform overhead) and RQ2 (cold-start): 5-way interaction over all predictors
model <- lmer(
  log(Runtime.Per.Sample) ~
    (Run + Buffer.Size + Iteration.Count + Environment + Model.Unique)^5
    + (1 | Repetition.Index),
  data = data
)

saveRDS(model, file.path(results_dir, "model_rq12.rds"))
message("RQ1 & RQ2 model (LMM-I) fitted.")

print(summary(model))
model_parameters(model)

perf <- model_performance(model)
print(perf)
print(performance::r2_nakagawa(model))

anova_result <- anova(model, ddf = "Kenward-Roger")
saveRDS(anova_result, file.path(results_dir, "anova_rq12.rds"))
print(anova_result)

# These significance thresholds are outdated. Ignore, and refer to significance-logging.r
significant     <- anova_result[anova_result$`Pr(>F)` <  0.0001, ]
non_significant <- anova_result[anova_result$`Pr(>F)` >= 0.0001, ]
message(paste("Significant (p < 0.0001):",     nrow(significant)))
message(paste("Non-significant (p >= 0.0001):", nrow(non_significant)))
print(significant)
print(non_significant)

source(here("source", "commands", "cleanup.r"))
q("no", save = "no")
