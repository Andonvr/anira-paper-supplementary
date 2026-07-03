library(here)
library(tidyverse)
library(lme4)
library(lmerTest)
library(performance)
library(parameters)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Exactly 1 argument must be supplied: <results_dir>")

results_dir <- args[1]
data <- readRDS(file.path(results_dir, "data_rq3.rds"))

# LMM-II for RQ3 (JS component overhead): factorial Backend × PP design, web-only, both models.
#
model <- lmer(
  log(Runtime.Per.Sample) ~
    (Backend + PP + Buffer.Size + Iteration.Count + Environment + Model.Unique)^5
    + (1 | Repetition.Index),
  data = data
)

saveRDS(model, file.path(results_dir, "model_rq3.rds"))
message("RQ3 model (LMM-II) fitted.")

print(summary(model))
model_parameters(model)

perf <- model_performance(model)
print(perf)
print(performance::r2_nakagawa(model))

anova_result <- anova(model, ddf = "Kenward-Roger")
saveRDS(anova_result, file.path(results_dir, "anova_rq3.rds"))
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
