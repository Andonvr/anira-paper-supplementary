library(here)
library(tidyverse)
library(lme4)
library(lmerTest)
library(emmeans)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Exactly 1 argument must be supplied: <results_dir>")

results_dir <- args[1]
data        <- readRDS(file.path(results_dir, "data_rq12.rds"))
model       <- readRDS(file.path(results_dir, "model_rq12.rds"))

emm_options(pbkrtest.limit = 200000, lmerTest.limit = 200000, rg.limit = 200000)

emm_analysis <- function(label = "", specs, method = "pairwise", adjust = "holm") {
  if (label != "") message(paste0("\n", label, "\n"))
  emm   <- emmeans(model, specs = specs, type = "response", data = data)
  contr <- contrast(emm, method = method, adjust = adjust)
  list(emm = emm, contr = contr)
}

# --- RQ1: Which environment is fastest? (platform overhead) ---

emm_analysis(label = "1.a Overall",   specs = ~ Environment,               method = "pairwise")
emm_analysis(label = "1.b By buffer size", specs = ~ Environment | Buffer.Size, method = "pairwise")

env_result <- emm_analysis(label = "1.c By run × model", specs = ~ Environment | Run * Model.Unique, method = "pairwise")
print(env_result$emm)
print(env_result$contr)

write.csv(as.data.frame(env_result$emm),   file.path(results_dir, "emm_rq1_environment.csv"),       row.names = FALSE)
write.csv(as.data.frame(env_result$contr), file.path(results_dir, "contrasts_rq1_environment.csv"), row.names = FALSE)
message("emm_rq1_environment.csv written to ", results_dir)

# --- RQ2: Do early iterations run slower? (cold-start) ---

emm_analysis(label = "2.a Overall",       specs = ~ Iteration.Count,                             method = "eff")
emm_analysis(label = "2.b By environment",specs = ~ Iteration.Count | Environment,               method = "eff")

iter_result <- emm_analysis(
  label  = "2.c By environment × run × model",
  specs  = ~ Iteration.Count | Environment * Run * Model.Unique,
  method = "eff"
)
print(iter_result$emm)
print(iter_result$contr)

iter_emm_df       <- as.data.frame(iter_result$emm)
iter_contrasts_df <- as.data.frame(iter_result$contr)

iter_emm_df$Iteration       <- as.numeric(as.character(iter_emm_df$Iteration.Count))
iter_contrasts_df$Iteration <- as.numeric(gsub("Iteration\\.Count(\\d+) effect", "\\1", iter_contrasts_df$contrast))

iter_emm_with_pval <- merge(
  iter_emm_df,
  iter_contrasts_df[, c("Environment", "Run", "Model.Unique", "Iteration", "p.value")],
  by    = c("Environment", "Run", "Model.Unique", "Iteration"),
  all.x = TRUE
)

write.csv(iter_emm_with_pval, file.path(results_dir, "emm_rq2_iterations.csv"), row.names = FALSE)
message("emm_rq2_iterations.csv written to ", results_dir)

source(here("source", "commands", "cleanup.r"))
q("no", save = "no")
