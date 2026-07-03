message(
  "\n",
  "#####################################################################\n",
  "# Clean up the environment\n",
  "#####################################################################\n"
)

message("Remaining attached packages:")
search()

message("Remaining objects in the environment:")
# Have a look at all the objects in the environment
ls()

message("Removing all objects from the environment...")
# Clean up the environment
rm(list = ls())

message("Remaining objects in the environment:")
ls()

# Clear memory
gc()