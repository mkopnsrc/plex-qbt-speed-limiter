# plex-qbt-speed-limiter

# Plex and qBittorrent Speed Limit Management Script

## Overview

This script manages the upload and download speed limits for qBittorrent based on Plex streaming activity. When someone is streaming from Plex, the script sets specific speed limits for qBittorrent. If no one is streaming, it removes these limits.

## Features

- Monitors Plex for current streaming sessions.
- Adjusts qBittorrent upload and download speed limits based on Plex streaming activity.
- If no streams found then, remove qBittorrent upload and download speed limits.
- Logs activity and errors to both console and a log file.

## Requirements

- Python 3.x
- `requests` library
- `qbittorrent-api` library
- `python-dotenv` library

### Install required libraries

    pip install -r requirements.txt

## Installation

1. **Clone the repository:**
    ```sh
    git clone https://github.com/mkopnsrc/plex-qbt-speed-limiter.git
    cd plex-qbt-speed-limiter
    ```

2. **Update environment file:**
    ```sh
    cp .env_SAMPLE .env
    vi .env
    ```

3. **Set Execute permission:**
    ```sh
    chmod u+x plex_qbt_speed_limiter.py
    ```

4. **Run script:**
    ```sh
    python3 plex_qbt_speed_limiter.py
    ```

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `PLEX_HOST` | Plex server host and port (e.g. `your-plex-host:32400`) | Yes |
| `PLEX_TOKEN` | Plex authentication token | Yes |
| `QBT_HOST` | qBittorrent Web UI host and port (e.g. `your-qbt-host:8080`) | Yes |
| `QBT_USER` | qBittorrent Web UI username | Yes |
| `QBT_PASS` | qBittorrent Web UI password | Yes |
| `UPLOAD_LIMIT_MBPS` | Upload speed limit in MB/s when someone is streaming (default: `0`) | No |
| `DOWNLOAD_LIMIT_MBPS` | Download speed limit in MB/s when someone is streaming (default: `0`) | No |
| `REQUIRE_SECURE_CONNECTION` | Set to `no` to use HTTP instead of HTTPS for the Plex connection (default: HTTPS) | No |
| `SLEEP_INTERVAL` | Seconds between each check for active Plex streams (default: `30`) | No |

## Docker

A Docker image is published to the GitHub Container Registry:

```
ghcr.io/mkopnsrc/plex-qbt-speed-limiter:latest
```

See the included `example-compose.yaml` for use with Docker Compose. No config files or volumes are needed — just set the environment variables.
