"""Shared fixtures for plex_qbt_speed_limiter tests."""

import importlib
import sys
import pytest


@pytest.fixture
def limiter_module(monkeypatch):
    """Import the main module with a fresh logger, avoiding side-effects.

    The module-level ``setup_logger()`` call runs on import, so we
    ensure the ``AM_I_IN_A_CONTAINER`` env var is set to ``yes`` to
    prevent file-handler creation during tests.
    """
    monkeypatch.setenv("AM_I_IN_A_CONTAINER", "yes")
    mod_name = "plex_qbt_speed_limiter"
    if mod_name in sys.modules:
        mod = importlib.reload(sys.modules[mod_name])
    else:
        mod = importlib.import_module(mod_name)
    return mod


@pytest.fixture
def mock_qbt_client(mocker):
    """Return a mocked qBittorrent Client instance."""
    client = mocker.MagicMock()
    client.transfer_upload_limit.return_value = 0
    client.transfer_download_limit.return_value = 0
    return client


PLEX_XML_STREAMING = """<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="1">
  <Video title="Test Movie" librarySectionTitle="Movies" grandparentTitle="" parentTitle="">
    <User title="testuser"/>
    <Player title="Chrome" local="1"/>
  </Video>
</MediaContainer>
"""

PLEX_XML_STREAMING_TV = """<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="1">
  <Video title="Pilot" librarySectionTitle="TV Shows" grandparentTitle="Breaking Bad" parentTitle="Season 1">
    <User title="tvuser"/>
    <Player title="Roku" local="0"/>
  </Video>
</MediaContainer>
"""

PLEX_XML_MULTIPLE_STREAMS = """<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="2">
  <Video title="Movie A" librarySectionTitle="Movies" grandparentTitle="" parentTitle="">
    <User title="user1"/>
    <Player title="Chrome" local="1"/>
  </Video>
  <Video title="Episode 1" librarySectionTitle="TV Shows" grandparentTitle="The Office" parentTitle="Season 1">
    <User title="user2"/>
    <Player title="AppleTV" local="0"/>
  </Video>
</MediaContainer>
"""

PLEX_XML_NO_STREAMS = """<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="0">
</MediaContainer>
"""
