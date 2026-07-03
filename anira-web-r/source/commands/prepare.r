library(here)
library(tidyverse)
library(pastecs)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4) stop("Exactly 4 arguments must be supplied: <csv_file> <max_iterations> <nth_iteration> <results_dir>")

csv_file       <- args[1]
max_iterations <- as.numeric(args[2])
nth_iteration  <- as.numeric(args[3])
results_dir    <- args[4]

dir.create(results_dir, recursive = TRUE, showWarnings = FALSE)

data <- read.csv(csv_file)

data$Model.Unique <- ifelse(data$Model == "steerable-nafx-libtorch-dynamic.onnx", "steerable-nafx",
                     ifelse(data$Model == "GuitarLSTM-libtorch-dynamic.onnx",      "guitar-lstm",
                     "none"))

data$Runtime.Per.Sample <- data$Runtime / data$Buffer.Size

data <- data %>% select(-Runtime, -Repetition.Count)

data <- data %>% filter(Iteration.Count %% nth_iteration == 0)
data <- data %>% filter(Iteration.Count <= max_iterations)

data$Model.Unique     <- factor(data$Model.Unique)
data$Run              <- factor(data$Run)
data$Environment      <- factor(data$Environment)
data$Buffer.Size      <- factor(data$Buffer.Size)
data$Iteration.Count  <- factor(data$Iteration.Count)
data$Repetition.Index <- factor(data$Repetition.Index)

contrasts(data$Iteration.Count) <- contr.sum(levels(data$Iteration.Count))

data$Model.Unique <- relevel(data$Model.Unique, ref = "guitar-lstm")
data$Run          <- relevel(data$Run,          ref = "bypass")
data$Environment  <- relevel(data$Environment,  ref = "Native")
data$Buffer.Size  <- relevel(data$Buffer.Size,  ref = "128")

# --- Datasets for RQ1 (platform overhead) and RQ2 (cold-start): bypass + onnx, all environments ---
data_rq12 <- data %>%
  filter(Run %in% c("bypass", "onnx")) %>%
  mutate(Run = droplevels(Run))

saveRDS(data_rq12, file.path(results_dir, "data_rq12.rds"))
message("data_rq12.rds written to ", results_dir)

# --- Dataset for RQ3 (JS component overhead): web only, both models, all 8 run configurations ---
web_runs <- c("bypass", "onnx", "js-bypass", "onnxrt-web",
              "bypass-jspp", "onnx-jspp", "js-bypass-jspp", "onnxrt-web-jspp")

backend_map <- c(
  "bypass"           = "wasm-bypass",
  "onnx"             = "wasm-onnx",
  "js-bypass"        = "js-bypass",
  "onnxrt-web"       = "js-onnx",
  "bypass-jspp"      = "wasm-bypass",
  "onnx-jspp"        = "wasm-onnx",
  "js-bypass-jspp"   = "js-bypass",
  "onnxrt-web-jspp"  = "js-onnx"
)
pp_map <- c(
  "bypass"           = "wasm",
  "onnx"             = "wasm",
  "js-bypass"        = "wasm",
  "onnxrt-web"       = "wasm",
  "bypass-jspp"      = "js",
  "onnx-jspp"        = "js",
  "js-bypass-jspp"   = "js",
  "onnxrt-web-jspp"  = "js"
)

data_rq3 <- data %>%
  filter(Environment != "Native") %>%
  filter(Run %in% web_runs) %>%
  mutate(
    Backend     = factor(backend_map[as.character(Run)]),
    PP          = factor(pp_map[as.character(Run)]),
    Run         = droplevels(Run),
    Environment = droplevels(Environment),
    Buffer.Size = droplevels(Buffer.Size),
    Model.Unique = droplevels(Model.Unique)
  )

data_rq3$Backend      <- relevel(data_rq3$Backend,      ref = "wasm-bypass")
data_rq3$PP           <- relevel(data_rq3$PP,           ref = "wasm")
data_rq3$Environment  <- relevel(data_rq3$Environment,  ref = "Chrome")

if (!identical(attr(data_rq3$Iteration.Count, "contrasts"), attr(data$Iteration.Count, "contrasts"))) {
  stop("contr.sum contrasts on Iteration.Count were lost during data_rq3 construction — models will use default treatment coding instead")
}

saveRDS(data_rq3, file.path(results_dir, "data_rq3.rds"))
message("data_rq3.rds written to ", results_dir)

source(here("source", "commands", "cleanup.r"))
q("no", save = "no")
