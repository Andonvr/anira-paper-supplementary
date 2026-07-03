library(here)
library(tidyverse)
library(lme4)
library(lmerTest)
library(emmeans)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("Exactly 1 argument must be supplied: <results_dir>")

results_dir <- args[1]
data        <- readRDS(file.path(results_dir, "data_rq3.rds"))
model       <- readRDS(file.path(results_dir, "model_rq3.rds"))
anova_rq3   <- readRDS(file.path(results_dir, "anova_rq3.rds"))

emm_options(pbkrtest.limit = 200000, lmerTest.limit = 200000, rg.limit = 200000)

emm_analysis <- function(label = "", specs, method = "pairwise", adjust = "holm") {
  if (label != "") message(paste0("\n", label, "\n"))
  emm   <- emmeans(model, specs = specs, type = "response", data = data)
  contr <- contrast(emm, method = method, adjust = adjust)
  list(emm = emm, contr = contr)
}

# --- RQ3a: JS backend cost (hold PP constant, per browser) ---

backend_result <- emm_analysis(
  label  = "Backend cost (hold PP constant, per browser × model)",
  specs  = ~ Backend | PP * Environment * Model.Unique,
  method = "pairwise"
)
print(backend_result$emm)
print(backend_result$contr)

write.csv(as.data.frame(backend_result$emm),   file.path(results_dir, "emm_rq3_backend.csv"),       row.names = FALSE)
write.csv(as.data.frame(backend_result$contr), file.path(results_dir, "contrasts_rq3_backend.csv"), row.names = FALSE)
message("emm_rq3_backend.csv written to ", results_dir)

# --- RQ3b: JS PP cost (hold backend constant, per browser) ---

pp_result <- emm_analysis(
  label  = "PP cost (hold backend constant, per browser × model)",
  specs  = ~ PP | Backend * Environment * Model.Unique,
  method = "pairwise"
)
print(pp_result$emm)
print(pp_result$contr)

write.csv(as.data.frame(pp_result$emm),   file.path(results_dir, "emm_rq3_pp.csv"),       row.names = FALSE)
write.csv(as.data.frame(pp_result$contr), file.path(results_dir, "contrasts_rq3_pp.csv"), row.names = FALSE)
message("emm_rq3_pp.csv written to ", results_dir)

# --- RQ3c: Full factorial Backend × PP per buffer size × browser (used for plotting) ---

factorial_result <- emm_analysis(
  label  = "Full factorial Backend × PP by buffer size × browser × model",
  specs  = ~ Backend * PP | Buffer.Size * Environment * Model.Unique,
  method = "pairwise"
)
print(factorial_result$emm)
print(factorial_result$contr)

write.csv(as.data.frame(factorial_result$emm),   file.path(results_dir, "emm_rq3_factorial.csv"),       row.names = FALSE)
write.csv(as.data.frame(factorial_result$contr), file.path(results_dir, "contrasts_rq3_factorial.csv"), row.names = FALSE)
message("emm_rq3_factorial.csv written to ", results_dir)

# --- RQ3 simplified: overhead averaged over the other factor, per browser ---
# Valid only if Backend:PP interaction is non-significant — verify from ANOVA first.

backend_pp_p <- anova_rq3["Backend:PP", "Pr(>F)"]
message(sprintf(
  "Backend:PP interaction: p = %.4g — %s",
  backend_pp_p,
  ifelse(backend_pp_p < 0.05,
         "SIGNIFICANT: averaging over the other factor may be misleading",
         "non-significant: averaging over the other factor is justified")
))

pp_simple <- emm_analysis(
  label  = "PP overhead (averaged over backends, per browser × model)",
  specs  = ~ PP | Environment * Model.Unique,
  method = "pairwise"
)
print(pp_simple$emm)
print(pp_simple$contr)
write.csv(as.data.frame(pp_simple$contr), file.path(results_dir, "contrasts_rq3_pp_simple.csv"),      row.names = FALSE)
message("contrasts_rq3_pp_simple.csv written to ", results_dir)

backend_simple <- emm_analysis(
  label  = "Backend overhead (averaged over PP, per browser × model)",
  specs  = ~ Backend | Environment * Model.Unique,
  method = "pairwise"
)
print(backend_simple$emm)
print(backend_simple$contr)
write.csv(as.data.frame(backend_simple$contr), file.path(results_dir, "contrasts_rq3_backend_simple.csv"), row.names = FALSE)
message("contrasts_rq3_backend_simple.csv written to ", results_dir)

source(here("source", "commands", "cleanup.r"))
q("no", save = "no")
