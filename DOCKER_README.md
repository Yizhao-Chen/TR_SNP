# TR_SNP Docker Usage Guide

## Overview

TR_SNP is a tool for selecting tree ring data from the ITRDB (International Tree-Ring Data Bank) and creating sub-datasets. When running TR_SNP in Docker, it's important to understand how data persistence works to avoid losing your downloaded data and metadata.

## Important Directories

TR_SNP uses three main directories that should be persisted between container runs:

1. **Cache Directory**: Stores processed metadata to avoid re-downloading
2. **Metadata Directory**: Stores output metadata files
3. **Data Directory**: Stores downloaded .rwl files

## Running with Docker

### Basic Run (Data will be lost when container stops)

```bash
docker run -it your-tr-snp-image
```

With this basic command, all data will be stored in temporary locations within the container and will be lost when the container stops.

### Recommended Run (With Data Persistence)

```bash
docker run -it \
  -v /host/path/to/cache:/app/cache \
  -v /host/path/to/metadata:/app/metadata \
  -v /host/path/to/data:/app/data \
  -e TR_SNP_CACHE_DIR=/app/cache \
  -e TR_SNP_METADATA_DIR=/app/metadata \
  -e TR_SNP_DATA_DIR=/app/data \
  your-tr-snp-image
```

Replace `/host/path/to/cache`, `/host/path/to/metadata`, and `/host/path/to/data` with directories on your host machine where you want to store the data.

## Environment Variables

TR_SNP supports the following environment variables for Docker:

| Variable | Description | Default |
|----------|-------------|---------|
| `TR_SNP_CACHE_DIR` | Directory for storing metadata cache | Temp directory if in Docker |
| `TR_SNP_METADATA_DIR` | Directory for storing metadata files | `./metadata` |
| `TR_SNP_DATA_DIR` | Directory for storing downloaded .rwl files | `./metadata/data` |

## Building the Docker Image

```bash
docker build -t tr-snp:latest .
```

## Checking Mounted Volumes

When TR_SNP starts, it will show information about the detected Docker environment and whether volumes are properly mounted. If you see "Not set - using temporary directory" for any path, data will be lost when the container stops.

## Recommendations

1. Always use volume mounts for all three directories to ensure data persistence
2. Use the same host directories consistently between runs
3. If you need to share data between different machines, consider using a shared network drive for your volumes 