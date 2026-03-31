"""Monitor Plex streaming sessions and limit qBittorrent speeds accordingly."""

from os import environ
from time import sleep
import logging
import xml.etree.ElementTree as ET
import requests
from qbittorrentapi import Client
from dotenv import load_dotenv

load_dotenv()

def setup_logger():
    """
    Creates a logger instance, sets logging levels, and attaches handlers for both 
    console and file output. Disable file output if in a container because the 
    container runtime is probably gonna log the console output. Probably.
    """
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()

    if environ.get("AM_I_IN_A_CONTAINER") != "yes":
        file_handler = logging.FileHandler('log.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)
        console_handler.setLevel(logging.INFO)
    else:
        console_handler.setLevel(logging.DEBUG)

    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)
    return log

logger = setup_logger()

def get_plex_sessions(plex_host, plex_token):
    """
    Retrieve the current streaming sessions from Plex.

    Returns:
        xml.etree.ElementTree.Element: The root element of the XML response from Plex API.
    """
    if environ.get("REQUIRE_SECURE_CONNECTION") == "no":
        endpoint = f'http://{plex_host}/status/sessions?X-Plex-Token={plex_token}'
    else:
        endpoint = f'https://{plex_host}/status/sessions?X-Plex-Token={plex_token}'
    try:
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        return ET.fromstring(response.content)
    except requests.RequestException as e:
        logger.error("Failed to retrieve sessions from Plex API: %s", e)
        return None

def mbps_to_bps(mbps):
    """
    Convert Megabytes per second (MB/s) to Bytes per second (B/s).
    """
    try:
        bps = int(float(mbps) * 1024 * 1024)
        return bps if bps > 0 else -1
    except ValueError:
        logger.error("Invalid limit value provided.")
        return -1

def get_current_qbt_limits(client):
    """
    Retrieve the current upload and download speed limits from qBittorrent.
    """
    try:
        current_upload_limit = client.transfer_upload_limit()
        current_download_limit = client.transfer_download_limit()
        logger.info("Current upload limit: %s B/s", current_upload_limit)
        logger.info("Current download limit: %s B/s", current_download_limit)
        return current_upload_limit, current_download_limit
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Failed to retrieve current speed limits from qBittorrent: %s", e)
        return None, None

def set_qbt_limits(client, upload_limit, download_limit):
    """
    Set the upload and download speed limits in qBittorrent.
    """
    try:
        client.transfer_set_upload_limit(upload_limit)
        client.transfer_set_download_limit(download_limit)
        if upload_limit != 0:
            logger.info("Upload speed limit set in qBittorrent.")
        else:
            logger.info("Removed upload speed limit in qBittorrent.")

        if download_limit != 0:
            logger.info("Download speed limit set in qBittorrent.")
        else:
            logger.info("Removed download speed limit in qBittorrent.")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Failed to set speed limits in qBittorrent: %s", e)

def process_plex_sessions(root, client, upload_limit, download_limit):
    """
    Process the Plex streaming sessions and set qBittorrent speed limits accordingly.
    """
    stream_count = root.attrib.get('size')
    logger.debug("Plex stream counts: %s", stream_count)
    if stream_count != "0":
        logger.info("Someone is streaming from Plex!")
        sessions = root.findall('./Video')
        for session in sessions:
            attributes          = session.attrib
            user                = session.find('./User').attrib['title']
            player              = session.find('./Player').attrib
            device_name         = player.get('title')
            library             = attributes.get('librarySectionTitle')
            grandparent_title   = attributes.get('grandparentTitle')
            parent_title        = attributes.get('parentTitle')
            title               = attributes.get('title')

            if grandparent_title:
                logger.info(
                    "User: %s, Device: %s, Library: %s, "
                    "Title: %s - %s - %s",
                    user, device_name, library,
                    grandparent_title, parent_title, title
                )
            else:
                logger.info(
                    "User: %s, Device: %s, Library: %s, Title: %s",
                    user, device_name, library, title
                )
        set_qbt_limits(client, upload_limit, download_limit)
    else:
        logger.info("No one is currently streaming from Plex.")
        set_qbt_limits(client, 0, 0)

def main():
    """
    Main function to initialize environment variables, create qBittorrent
    client, and run the main loop.
    """
    plex_host           = environ.get("PLEX_HOST")
    plex_token          = environ.get("PLEX_TOKEN")
    qbt_host            = environ.get("QBT_HOST")
    qbt_user            = environ.get("QBT_USER")
    qbt_pass            = environ.get("QBT_PASS")
    upload_limit_mbps   = environ.get("UPLOAD_LIMIT_MBPS", "0")
    download_limit_mbps = environ.get("DOWNLOAD_LIMIT_MBPS", "0")
    sleep_interval      = int(environ.get("SLEEP_INTERVAL", "30"))

    if not all([plex_host, plex_token, qbt_host, qbt_user, qbt_pass]):
        logger.error("One or more environment variables are missing.")
        return

    client = Client(host=qbt_host, username=qbt_user, password=qbt_pass)
    upload_limit    = mbps_to_bps(upload_limit_mbps)
    download_limit  = mbps_to_bps(download_limit_mbps)

    while True:
        get_current_qbt_limits(client)
        root = get_plex_sessions(plex_host, plex_token)
        process_plex_sessions(root, client, upload_limit, download_limit)
        sleep(sleep_interval)

if __name__ == "__main__":
    main()
