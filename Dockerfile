FROM python:3.7-slim

# Install system dependencies, R and required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    r-base-dev \
    libssl-dev \
    libcurl4-openssl-dev \
    libxml2-dev \
    git \
    build-essential \
    tk \
    libx11-6 \
    libxext-dev \
    libxrender-dev \
    libxtst-dev \
    && rm -rf /var/lib/apt/lists/*

# Install required R packages
RUN R -e "install.packages(c('dplR', 'ggplot2', 'tidyverse'), repos='https://cran.rstudio.com/')"

# Set environment variables for rpy2
ENV R_HOME=/usr/lib/R
ENV LD_LIBRARY_PATH=/usr/lib/R/lib:$LD_LIBRARY_PATH

# Set working directory
WORKDIR /app

# Copy the Python requirements first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create necessary directories if they don't exist
RUN mkdir -p test_output cache test_cache metadata

# Set the DISPLAY variable
ENV DISPLAY=:0

# Default command
CMD ["python", "TR_SNP.py"] 