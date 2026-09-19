# print the current R version
R.version.string

# Install packages
# ggplot2 is part of the tidyverse, so we don't need to install it separately
install.packages("here", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32)
install.packages("tidyverse", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32)
install.packages("lme4", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32)
install.packages("lmerTest", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32)
install.packages("performance", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32)
install.packages("parameters", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32) # two packages are failing here in r-base image but they are not required hopefully (ClassDiscovery and PCDimension)
install.packages("sjPlot", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32)
install.packages("emmeans", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32)
install.packages("patchwork", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32)
install.packages("pastecs", dependencies = TRUE, repos = "https://cloud.r-project.org", Ncpus = 32)
