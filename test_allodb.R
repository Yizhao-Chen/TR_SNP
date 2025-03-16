#!/usr/bin/env Rscript

# Script to test if allodb is correctly installed
message("Testing allodb installation...")

# Check if allodb is installed, attempt to install if missing
if (!require("allodb", quietly = TRUE)) {
  message("allodb package not found, attempting to install...")
  
  # Try to install via remotes if available
  if (require("remotes", quietly = TRUE)) {
    remotes::install_github("ropensci/allodb")
  } else {
    # Try to install remotes first
    install.packages("remotes", repos = "https://cloud.r-project.org/")
    if (require("remotes", quietly = TRUE)) {
      remotes::install_github("ropensci/allodb")
    } else {
      message("Error: Failed to install remotes package")
      quit(status = 1)
    }
  }
  
  # Check if installation succeeded
  if (!require("allodb", quietly = TRUE)) {
    message("Error: Failed to install allodb package")
    quit(status = 1)
  }
} else {
  message("Success: allodb package loaded successfully")
}

# Test functionality
message("Available datasets in allodb:")
data(package = "allodb")

message("Loading sample data from allodb...")
data("missing_values", package = "allodb")
message("Sample data from allodb:")
print(head(missing_values))

message("Test completed successfully") 