# plex-qbt-speed-limiter

# Plex and qBittorrent Speed Limit Management Script

## Overview

This script manages the upload and download speed limits for qBittorrent based on Plex streaming activity. When someone is streaming from Plex, the script sets specific speed limits for qBittorrent. If no one is streaming, it removes these limits.

## Features

- Monitors Plex for current streaming sessions.
- Adjusts qBittorrent upload and download speed limits based on Plex streaming activity.
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
    chmod u+x qbt_rate_limiter.py
    python3 qbt_rate_limiter.py

