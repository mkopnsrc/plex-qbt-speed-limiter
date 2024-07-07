import requests
import xml.etree.ElementTree as ET
from qbittorrentapi import Client
import logging
from time import sleep
from dotenv import load_dotenv
from os import environ

load_dotenv()

def setup_logger():
    #Creates a logger instance, sets logging levels, and attaches handlers for both console and file output.
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('log.log')
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger()

def get_plex_sessions(plex_host, plex_token):
    #Retrieve the current streaming sessions from Plex.
    """
    Returns:
    xml.etree.ElementTree.Element: The root element of the XML response from Plex API.
    """
    endpoint = f'https://{plex_host}/status/sessions?X-Plex-Token={plex_token}'
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        return ET.fromstring(response.content)
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve sessions from Plex API: {e}")
        return None

def mbps_to_bps(mbps):
    #Convert Megabytes per second (MB/s) to Bytes per second (B/s).
    try:
        bps = int(float(mbps) * 1024 * 1024)
        return bps if bps > 0 else -1
    except ValueError:
        logger.error("Invalid limit value provided.")
        return -1

def get_current_qbt_limits(client):
    #Retrieve the current upload and download speed limits from qBittorrent.
    try:
        current_upload_limit = client.transfer_upload_limit()
        current_download_limit = client.transfer_download_limit()
        logger.info(f"Current upload limit: {current_upload_limit} B/s")
        logger.info(f"Current download limit: {current_download_limit} B/s")
        return current_upload_limit, current_download_limit
    except Exception as e:
        logger.error(f"Failed to retrieve current speed limits from qBittorrent: {e}")
        return None, None

def set_qbt_limits(client, upload_limit, download_limit):
    #Set the upload and download speed limits in qBittorrent.
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
    except Exception as e:
        logger.error(f"Failed to set speed limits in qBittorrent: {e}")

def process_plex_sessions(root, client, upload_limit, download_limit):
    #Process the Plex streaming sessions and set qBittorrent speed limits accordingly.
    stream_count = root.attrib.get('size')
    logger.debug(f"Plex stream counts: {stream_count}")
    if stream_count != "0":
        logger.info("Someone is streaming from Plex!")
        sessions = root.findall('./Video')
        for session in sessions:
            attributes = session.attrib
            user = session.find('./User').attrib['title']
            player = session.find('./Player').attrib
            stream_type = player.get('local')
            device_name = player.get('title')
            library = attributes.get('librarySectionTitle')
            grandparent_title = attributes.get('grandparentTitle')
            parent_title = attributes.get('parentTitle')
            title = attributes.get('title')

            if grandparent_title:
                logger.info(f"User: {user}, Device: {device_name}, Library: {library}, Title: {grandparent_title} - {parent_title} - {title}")
            else:
                logger.info(f"User: {user}, Device: {device_name}, Library: {library}, Title: {title}")
        set_qbt_limits(client, upload_limit, download_limit)
    else:
        logger.info("No one is currently streaming from Plex.")
        set_qbt_limits(client, 0, 0)

def main():
    # Main function to initialize environment variables, create qBittorrent client, and run the main loop
    plex_host = environ.get("PLEX_HOST")
    plex_token = environ.get("PLEX_TOKEN")
    qbt_host = environ.get("QBT_HOST")
    qbt_user = environ.get("QBT_USER")
    qbt_pass = environ.get("QBT_PASS")
    upload_limit_mbps = environ.get("UPLOAD_LIMIT_MBPS", "0")
    download_limit_mbps = environ.get("DOWNLOAD_LIMIT_MBPS", "0")

    if not all([plex_host, plex_token, qbt_host, qbt_user, qbt_pass]):
        logger.error("One or more environment variables are missing.")
        return

    client = Client(host=qbt_host, username=qbt_user, password=qbt_pass)
    upload_limit = mbps_to_bps(upload_limit_mbps)
    download_limit = mbps_to_bps(download_limit_mbps)

    while True:
        current_upload_limit, current_download_limit = get_current_qbt_limits(client)
        root = get_plex_sessions(plex_host, plex_token)
        process_plex_sessions(root, client, upload_limit, download_limit)
        sleep(30)

if __name__ == "__main__":
    main()

