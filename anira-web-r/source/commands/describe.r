library(here)
library(tidyverse)
library(pastecs)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Exactly 1 argument must be supplied: <results_dir>")

results_dir <- args[1]

# Use the RQ1/RQ2 dataset (bypass + onnx, all environments); filter to bypass to isolate framework overhead
data <- readRDS(file.path(results_dir, "data_rq12.rds")) %>%
  filter(Run == "bypass")

environments <- levels(droplevels(data$Environment))
models       <- levels(droplevels(data$Model.Unique))

rows <- list()
for (env_name in environments) {
  for (model_name in models) {
    subset <- data %>%
      filter(Environment == env_name, Model.Unique == model_name)

    if (nrow(subset) == 0) next

    # Aggregate to repetition level before computing SE — iterations within a
    # repetition share a cold-start baseline and are not independent observations.
    rep_means <- subset %>%
      group_by(Repetition.Index) %>%
      summarise(rep_mean = mean(Runtime.Per.Sample), .groups = "drop")

    stats    <- stat.desc(rep_means["rep_mean"])
    mean_val <- stats["mean",         "rep_mean"]
    se_val   <- stats["SE.mean",      "rep_mean"]
    ci_val   <- stats["CI.mean.0.95", "rep_mean"]

    rows[[length(rows) + 1]] <- data.frame(
      Environment = env_name,
      Model       = model_name,
      Mean        = mean_val,
      SE          = se_val,
      CI_Lower    = mean_val - ci_val,
      CI_Upper    = mean_val + ci_val,
      stringsAsFactors = FALSE
    )
  }
}

describe_df <- bind_rows(rows)
write.csv(describe_df, file.path(results_dir, "describe.csv"), row.names = FALSE)
message("describe.csv written to ", results_dir)

source(here("source", "commands", "cleanup.r"))
q("no", save = "no")
