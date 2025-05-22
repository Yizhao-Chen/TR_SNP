# TR-SNP Docker Usage

This document provides instructions for building and running the TR-SNP project as a Docker container.

## Prerequisites

- Docker installed on your system
- Git (to clone the repository if needed)

## Building the Docker Image

1. Navigate to the TR-SNP project root directory
2. Build the Docker image:

```bash
docker build -t tr-snp .
```

This command will build a Docker image named 'tr-snp' based on the Dockerfile in the current directory.

## Running the Container

To run the TR-SNP application:

```bash
docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix tr-snp
```

### For Windows users:

If you're using Windows with X server (like VcXsrv):

1. Install and start VcXsrv or another X server
2. Run with:

```powershell
docker run -it --rm -e DISPLAY=host.docker.internal:0 tr-snp
```

## Mounting Data Volumes

To access your local files from within the container:

```bash
docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v /path/to/your/data:/app/data tr-snp
```

Replace `/path/to/your/data` with the actual path to your data directory.

## Customizing the Command

To run a specific script or command:

```bash
docker run -it --rm tr-snp python other_script.py
```

## Troubleshooting

### X11 Display Issues

If you encounter issues with the GUI display:

1. Ensure your X server is running and properly configured
2. Try using the `--network=host` option:

```bash
docker run -it --rm --network=host -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix tr-snp
```

### Permission Issues

If you encounter permission issues with mounted volumes:

```bash
docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v /path/to/your/data:/app/data:Z tr-snp
``` 