"""Comprehensive tests for plex-qbt-speed-limiter.py."""

import logging
import xml.etree.ElementTree as ET

import pytest
import responses

from tests.conftest import (
    PLEX_XML_MULTIPLE_STREAMS,
    PLEX_XML_NO_STREAMS,
    PLEX_XML_STREAMING,
    PLEX_XML_STREAMING_TV,
)


# ---------------------------------------------------------------------------
# mbps_to_bps
# ---------------------------------------------------------------------------
class TestMbpsToBps:
    """Tests for the mbps_to_bps conversion function."""

    def test_converts_integer_mbps(self, limiter_module):
        assert limiter_module.mbps_to_bps(10) == 10 * 1024 * 1024

    def test_converts_string_integer(self, limiter_module):
        assert limiter_module.mbps_to_bps("10") == 10 * 1024 * 1024

    def test_converts_float(self, limiter_module):
        assert limiter_module.mbps_to_bps(1.5) == int(1.5 * 1024 * 1024)

    def test_converts_string_float(self, limiter_module):
        assert limiter_module.mbps_to_bps("2.5") == int(2.5 * 1024 * 1024)

    def test_one_mbps(self, limiter_module):
        assert limiter_module.mbps_to_bps(1) == 1048576

    def test_zero_returns_negative_one(self, limiter_module):
        assert limiter_module.mbps_to_bps(0) == -1

    def test_string_zero_returns_negative_one(self, limiter_module):
        assert limiter_module.mbps_to_bps("0") == -1

    def test_negative_returns_negative_one(self, limiter_module):
        assert limiter_module.mbps_to_bps(-5) == -1

    def test_string_negative_returns_negative_one(self, limiter_module):
        assert limiter_module.mbps_to_bps("-10") == -1

    def test_invalid_string_returns_negative_one(self, limiter_module):
        assert limiter_module.mbps_to_bps("abc") == -1

    def test_empty_string_returns_negative_one(self, limiter_module):
        assert limiter_module.mbps_to_bps("") == -1

    def test_none_raises_type_error(self, limiter_module):
        # float(None) raises TypeError which is not caught by the ValueError handler
        with pytest.raises(TypeError):
            limiter_module.mbps_to_bps(None)

    def test_very_large_value(self, limiter_module):
        result = limiter_module.mbps_to_bps(1000)
        assert result == 1000 * 1024 * 1024

    def test_very_small_positive_float(self, limiter_module):
        # 0.000001 * 1024 * 1024 = ~1.048  -> int = 1 -> > 0 so returns 1
        result = limiter_module.mbps_to_bps(0.000001)
        assert result == int(0.000001 * 1024 * 1024)
        assert result > 0


# ---------------------------------------------------------------------------
# setup_logger
# ---------------------------------------------------------------------------
class TestSetupLogger:
    """Tests for the setup_logger function."""

    def test_returns_logger_instance(self, limiter_module):
        new_logger = limiter_module.setup_logger()
        assert isinstance(new_logger, logging.Logger)

    def test_logger_level_is_debug(self, limiter_module):
        new_logger = limiter_module.setup_logger()
        assert new_logger.level == logging.DEBUG

    def test_container_mode_no_file_handler(self, limiter_module, monkeypatch):
        monkeypatch.setenv("AM_I_IN_A_CONTAINER", "yes")
        new_logger = limiter_module.setup_logger()
        file_handlers = [h for h in new_logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0

    def test_container_mode_console_at_debug(self, limiter_module, monkeypatch):
        monkeypatch.setenv("AM_I_IN_A_CONTAINER", "yes")
        new_logger = limiter_module.setup_logger()
        stream_handlers = [
            h for h in new_logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert any(h.level == logging.DEBUG for h in stream_handlers)

    def test_non_container_mode_has_file_handler(self, limiter_module, monkeypatch, tmp_path):
        monkeypatch.delenv("AM_I_IN_A_CONTAINER", raising=False)
        monkeypatch.chdir(tmp_path)
        new_logger = limiter_module.setup_logger()
        file_handlers = [h for h in new_logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) >= 1
        # Clean up handlers to release file
        for h in file_handlers:
            h.close()
            new_logger.removeHandler(h)

    def test_non_container_mode_console_at_info(self, limiter_module, monkeypatch, tmp_path):
        monkeypatch.delenv("AM_I_IN_A_CONTAINER", raising=False)
        monkeypatch.chdir(tmp_path)
        new_logger = limiter_module.setup_logger()
        stream_handlers = [
            h for h in new_logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert any(h.level == logging.INFO for h in stream_handlers)
        # Clean up
        for h in new_logger.handlers:
            if isinstance(h, logging.FileHandler):
                h.close()
                new_logger.removeHandler(h)

    def test_formatter_contains_expected_fields(self, limiter_module):
        new_logger = limiter_module.setup_logger()
        for handler in new_logger.handlers:
            fmt = handler.formatter._fmt
            assert "asctime" in fmt
            assert "levelname" in fmt
            assert "message" in fmt


# ---------------------------------------------------------------------------
# get_plex_sessions
# ---------------------------------------------------------------------------
class TestGetPlexSessions:
    """Tests for the get_plex_sessions function."""

    @responses.activate
    def test_successful_https_request(self, limiter_module, monkeypatch):
        monkeypatch.delenv("REQUIRE_SECURE_CONNECTION", raising=False)
        responses.add(
            responses.GET,
            "https://plex.local/status/sessions",
            body=PLEX_XML_STREAMING,
            status=200,
        )
        root = limiter_module.get_plex_sessions("plex.local", "testtoken")
        assert root is not None
        assert root.tag == "MediaContainer"
        assert root.attrib["size"] == "1"

    @responses.activate
    def test_successful_http_request_insecure(self, limiter_module, monkeypatch):
        monkeypatch.setenv("REQUIRE_SECURE_CONNECTION", "no")
        responses.add(
            responses.GET,
            "http://plex.local/status/sessions",
            body=PLEX_XML_NO_STREAMS,
            status=200,
        )
        root = limiter_module.get_plex_sessions("plex.local", "testtoken")
        assert root is not None
        assert root.attrib["size"] == "0"

    @responses.activate
    def test_http_error_returns_none(self, limiter_module, monkeypatch):
        monkeypatch.delenv("REQUIRE_SECURE_CONNECTION", raising=False)
        responses.add(
            responses.GET,
            "https://plex.local/status/sessions",
            status=500,
        )
        root = limiter_module.get_plex_sessions("plex.local", "testtoken")
        assert root is None

    @responses.activate
    def test_401_unauthorized_returns_none(self, limiter_module, monkeypatch):
        monkeypatch.delenv("REQUIRE_SECURE_CONNECTION", raising=False)
        responses.add(
            responses.GET,
            "https://plex.local/status/sessions",
            status=401,
        )
        root = limiter_module.get_plex_sessions("plex.local", "testtoken")
        assert root is None

    @responses.activate
    def test_connection_error_returns_none(self, limiter_module, monkeypatch):
        monkeypatch.delenv("REQUIRE_SECURE_CONNECTION", raising=False)
        import requests as req_lib
        responses.add(
            responses.GET,
            "https://plex.local/status/sessions",
            body=req_lib.ConnectionError("Connection refused"),
        )
        root = limiter_module.get_plex_sessions("plex.local", "testtoken")
        assert root is None

    @responses.activate
    def test_secure_connection_default(self, limiter_module, monkeypatch):
        """When REQUIRE_SECURE_CONNECTION is not 'no', HTTPS is used."""
        monkeypatch.setenv("REQUIRE_SECURE_CONNECTION", "yes")
        responses.add(
            responses.GET,
            "https://plex.local/status/sessions",
            body=PLEX_XML_NO_STREAMS,
            status=200,
        )
        root = limiter_module.get_plex_sessions("plex.local", "testtoken")
        assert root is not None

    @responses.activate
    def test_returns_valid_xml_root(self, limiter_module, monkeypatch):
        monkeypatch.delenv("REQUIRE_SECURE_CONNECTION", raising=False)
        responses.add(
            responses.GET,
            "https://plex.local/status/sessions",
            body=PLEX_XML_STREAMING_TV,
            status=200,
        )
        root = limiter_module.get_plex_sessions("plex.local", "testtoken")
        videos = root.findall("./Video")
        assert len(videos) == 1
        assert videos[0].attrib["grandparentTitle"] == "Breaking Bad"


# ---------------------------------------------------------------------------
# get_current_qbt_limits
# ---------------------------------------------------------------------------
class TestGetCurrentQbtLimits:
    """Tests for the get_current_qbt_limits function."""

    def test_returns_upload_and_download(self, limiter_module, mock_qbt_client):
        mock_qbt_client.transfer_upload_limit.return_value = 1048576
        mock_qbt_client.transfer_download_limit.return_value = 2097152
        up, down = limiter_module.get_current_qbt_limits(mock_qbt_client)
        assert up == 1048576
        assert down == 2097152

    def test_returns_zero_when_unlimited(self, limiter_module, mock_qbt_client):
        mock_qbt_client.transfer_upload_limit.return_value = 0
        mock_qbt_client.transfer_download_limit.return_value = 0
        up, down = limiter_module.get_current_qbt_limits(mock_qbt_client)
        assert up == 0
        assert down == 0

    def test_returns_none_on_exception(self, limiter_module, mock_qbt_client):
        mock_qbt_client.transfer_upload_limit.side_effect = Exception("API error")
        up, down = limiter_module.get_current_qbt_limits(mock_qbt_client)
        assert up is None
        assert down is None

    def test_calls_client_methods(self, limiter_module, mock_qbt_client):
        limiter_module.get_current_qbt_limits(mock_qbt_client)
        mock_qbt_client.transfer_upload_limit.assert_called_once()
        mock_qbt_client.transfer_download_limit.assert_called_once()


# ---------------------------------------------------------------------------
# set_qbt_limits
# ---------------------------------------------------------------------------
class TestSetQbtLimits:
    """Tests for the set_qbt_limits function."""

    def test_sets_nonzero_limits(self, limiter_module, mock_qbt_client):
        limiter_module.set_qbt_limits(mock_qbt_client, 1048576, 2097152)
        mock_qbt_client.transfer_set_upload_limit.assert_called_once_with(1048576)
        mock_qbt_client.transfer_set_download_limit.assert_called_once_with(2097152)

    def test_sets_zero_limits_to_remove(self, limiter_module, mock_qbt_client):
        limiter_module.set_qbt_limits(mock_qbt_client, 0, 0)
        mock_qbt_client.transfer_set_upload_limit.assert_called_once_with(0)
        mock_qbt_client.transfer_set_download_limit.assert_called_once_with(0)

    def test_handles_exception(self, limiter_module, mock_qbt_client):
        mock_qbt_client.transfer_set_upload_limit.side_effect = Exception("API error")
        # Should not raise
        limiter_module.set_qbt_limits(mock_qbt_client, 100, 200)

    def test_logs_set_message_for_nonzero_upload(self, limiter_module, mock_qbt_client, caplog):
        with caplog.at_level(logging.INFO):
            limiter_module.set_qbt_limits(mock_qbt_client, 1048576, 0)
        assert "Upload speed limit set" in caplog.text

    def test_logs_removed_message_for_zero_upload(self, limiter_module, mock_qbt_client, caplog):
        with caplog.at_level(logging.INFO):
            limiter_module.set_qbt_limits(mock_qbt_client, 0, 0)
        assert "Removed upload speed limit" in caplog.text

    def test_logs_set_message_for_nonzero_download(self, limiter_module, mock_qbt_client, caplog):
        with caplog.at_level(logging.INFO):
            limiter_module.set_qbt_limits(mock_qbt_client, 0, 2097152)
        assert "Download speed limit set" in caplog.text

    def test_logs_removed_message_for_zero_download(self, limiter_module, mock_qbt_client, caplog):
        with caplog.at_level(logging.INFO):
            limiter_module.set_qbt_limits(mock_qbt_client, 0, 0)
        assert "Removed download speed limit" in caplog.text

    def test_logs_error_on_exception(self, limiter_module, mock_qbt_client, caplog):
        mock_qbt_client.transfer_set_upload_limit.side_effect = Exception("fail")
        with caplog.at_level(logging.ERROR):
            limiter_module.set_qbt_limits(mock_qbt_client, 100, 200)
        assert "Failed to set speed limits" in caplog.text


# ---------------------------------------------------------------------------
# process_plex_sessions
# ---------------------------------------------------------------------------
class TestProcessPlexSessions:
    """Tests for the process_plex_sessions function."""

    def test_streaming_sets_limits(self, limiter_module, mock_qbt_client):
        root = ET.fromstring(PLEX_XML_STREAMING)
        limiter_module.process_plex_sessions(root, mock_qbt_client, 1048576, 2097152)
        mock_qbt_client.transfer_set_upload_limit.assert_called_once_with(1048576)
        mock_qbt_client.transfer_set_download_limit.assert_called_once_with(2097152)

    def test_no_streaming_removes_limits(self, limiter_module, mock_qbt_client):
        root = ET.fromstring(PLEX_XML_NO_STREAMS)
        limiter_module.process_plex_sessions(root, mock_qbt_client, 1048576, 2097152)
        mock_qbt_client.transfer_set_upload_limit.assert_called_once_with(0)
        mock_qbt_client.transfer_set_download_limit.assert_called_once_with(0)

    def test_multiple_streams_sets_limits(self, limiter_module, mock_qbt_client):
        root = ET.fromstring(PLEX_XML_MULTIPLE_STREAMS)
        limiter_module.process_plex_sessions(root, mock_qbt_client, 1048576, 2097152)
        mock_qbt_client.transfer_set_upload_limit.assert_called_once_with(1048576)
        mock_qbt_client.transfer_set_download_limit.assert_called_once_with(2097152)

    def test_logs_streaming_message(self, limiter_module, mock_qbt_client, caplog):
        root = ET.fromstring(PLEX_XML_STREAMING)
        with caplog.at_level(logging.INFO):
            limiter_module.process_plex_sessions(root, mock_qbt_client, 1048576, 2097152)
        assert "Someone is streaming from Plex" in caplog.text

    def test_logs_not_streaming_message(self, limiter_module, mock_qbt_client, caplog):
        root = ET.fromstring(PLEX_XML_NO_STREAMS)
        with caplog.at_level(logging.INFO):
            limiter_module.process_plex_sessions(root, mock_qbt_client, 1048576, 2097152)
        assert "No one is currently streaming" in caplog.text

    def test_logs_movie_title_without_grandparent(self, limiter_module, mock_qbt_client, caplog):
        root = ET.fromstring(PLEX_XML_STREAMING)
        with caplog.at_level(logging.INFO):
            limiter_module.process_plex_sessions(root, mock_qbt_client, 1048576, 2097152)
        assert "Test Movie" in caplog.text
        assert "testuser" in caplog.text
        assert "Chrome" in caplog.text

    def test_logs_tv_show_with_grandparent_title(self, limiter_module, mock_qbt_client, caplog):
        root = ET.fromstring(PLEX_XML_STREAMING_TV)
        with caplog.at_level(logging.INFO):
            limiter_module.process_plex_sessions(root, mock_qbt_client, 1048576, 2097152)
        assert "Breaking Bad" in caplog.text
        assert "Season 1" in caplog.text
        assert "Pilot" in caplog.text
        assert "tvuser" in caplog.text

    def test_logs_stream_count(self, limiter_module, mock_qbt_client, caplog):
        root = ET.fromstring(PLEX_XML_MULTIPLE_STREAMS)
        with caplog.at_level(logging.DEBUG):
            limiter_module.process_plex_sessions(root, mock_qbt_client, 1048576, 2097152)
        assert "2" in caplog.text

    def test_multiple_streams_logs_all_users(self, limiter_module, mock_qbt_client, caplog):
        root = ET.fromstring(PLEX_XML_MULTIPLE_STREAMS)
        with caplog.at_level(logging.INFO):
            limiter_module.process_plex_sessions(root, mock_qbt_client, 1048576, 2097152)
        assert "user1" in caplog.text
        assert "user2" in caplog.text


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
class TestMain:
    """Tests for the main function."""

    def test_exits_early_when_plex_host_missing(self, limiter_module, monkeypatch, caplog):
        monkeypatch.delenv("PLEX_HOST", raising=False)
        monkeypatch.setenv("PLEX_TOKEN", "token")
        monkeypatch.setenv("QBT_HOST", "qbt")
        monkeypatch.setenv("QBT_USER", "user")
        monkeypatch.setenv("QBT_PASS", "pass")
        with caplog.at_level(logging.ERROR):
            limiter_module.main()
        assert "missing" in caplog.text.lower()

    def test_exits_early_when_plex_token_missing(self, limiter_module, monkeypatch, caplog):
        monkeypatch.setenv("PLEX_HOST", "host")
        monkeypatch.delenv("PLEX_TOKEN", raising=False)
        monkeypatch.setenv("QBT_HOST", "qbt")
        monkeypatch.setenv("QBT_USER", "user")
        monkeypatch.setenv("QBT_PASS", "pass")
        with caplog.at_level(logging.ERROR):
            limiter_module.main()
        assert "missing" in caplog.text.lower()

    def test_exits_early_when_qbt_host_missing(self, limiter_module, monkeypatch, caplog):
        monkeypatch.setenv("PLEX_HOST", "host")
        monkeypatch.setenv("PLEX_TOKEN", "token")
        monkeypatch.delenv("QBT_HOST", raising=False)
        monkeypatch.setenv("QBT_USER", "user")
        monkeypatch.setenv("QBT_PASS", "pass")
        with caplog.at_level(logging.ERROR):
            limiter_module.main()
        assert "missing" in caplog.text.lower()

    def test_exits_early_when_qbt_user_missing(self, limiter_module, monkeypatch, caplog):
        monkeypatch.setenv("PLEX_HOST", "host")
        monkeypatch.setenv("PLEX_TOKEN", "token")
        monkeypatch.setenv("QBT_HOST", "qbt")
        monkeypatch.delenv("QBT_USER", raising=False)
        monkeypatch.setenv("QBT_PASS", "pass")
        with caplog.at_level(logging.ERROR):
            limiter_module.main()
        assert "missing" in caplog.text.lower()

    def test_exits_early_when_qbt_pass_missing(self, limiter_module, monkeypatch, caplog):
        monkeypatch.setenv("PLEX_HOST", "host")
        monkeypatch.setenv("PLEX_TOKEN", "token")
        monkeypatch.setenv("QBT_HOST", "qbt")
        monkeypatch.setenv("QBT_USER", "user")
        monkeypatch.delenv("QBT_PASS", raising=False)
        with caplog.at_level(logging.ERROR):
            limiter_module.main()
        assert "missing" in caplog.text.lower()

    def test_exits_early_when_all_env_vars_missing(self, limiter_module, monkeypatch, caplog):
        for var in ("PLEX_HOST", "PLEX_TOKEN", "QBT_HOST", "QBT_USER", "QBT_PASS"):
            monkeypatch.delenv(var, raising=False)
        with caplog.at_level(logging.ERROR):
            limiter_module.main()
        assert "missing" in caplog.text.lower()

    def test_main_loop_runs_and_stops(self, limiter_module, monkeypatch, mocker):
        """Test that main() creates a Client and enters the loop."""
        monkeypatch.setenv("PLEX_HOST", "plex.local")
        monkeypatch.setenv("PLEX_TOKEN", "tok123")
        monkeypatch.setenv("QBT_HOST", "qbt.local")
        monkeypatch.setenv("QBT_USER", "admin")
        monkeypatch.setenv("QBT_PASS", "secret")
        monkeypatch.setenv("UPLOAD_LIMIT_MBPS", "10")
        monkeypatch.setenv("DOWNLOAD_LIMIT_MBPS", "20")

        mock_client_instance = mocker.MagicMock()
        mock_client_instance.transfer_upload_limit.return_value = 0
        mock_client_instance.transfer_download_limit.return_value = 0
        mock_client_cls = mocker.MagicMock(return_value=mock_client_instance)
        monkeypatch.setattr(limiter_module, "Client", mock_client_cls)

        mock_get_sessions = mocker.MagicMock(
            return_value=ET.fromstring(PLEX_XML_NO_STREAMS)
        )
        monkeypatch.setattr(limiter_module, "get_plex_sessions", mock_get_sessions)

        call_count = 0

        def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise KeyboardInterrupt()

        monkeypatch.setattr(limiter_module, "sleep", mock_sleep)

        with pytest.raises(KeyboardInterrupt):
            limiter_module.main()

        mock_client_cls.assert_called_once_with(
            host="qbt.local", username="admin", password="secret"
        )
        assert mock_get_sessions.call_count >= 1

    def test_default_limits_when_not_set(self, limiter_module, monkeypatch, mocker):
        """UPLOAD_LIMIT_MBPS and DOWNLOAD_LIMIT_MBPS default to '0'."""
        monkeypatch.setenv("PLEX_HOST", "plex.local")
        monkeypatch.setenv("PLEX_TOKEN", "tok123")
        monkeypatch.setenv("QBT_HOST", "qbt.local")
        monkeypatch.setenv("QBT_USER", "admin")
        monkeypatch.setenv("QBT_PASS", "secret")
        monkeypatch.delenv("UPLOAD_LIMIT_MBPS", raising=False)
        monkeypatch.delenv("DOWNLOAD_LIMIT_MBPS", raising=False)

        mock_client_instance = mocker.MagicMock()
        mock_client_instance.transfer_upload_limit.return_value = 0
        mock_client_instance.transfer_download_limit.return_value = 0
        mock_client_cls = mocker.MagicMock(return_value=mock_client_instance)
        monkeypatch.setattr(limiter_module, "Client", mock_client_cls)

        monkeypatch.setattr(
            limiter_module,
            "get_plex_sessions",
            mocker.MagicMock(return_value=ET.fromstring(PLEX_XML_NO_STREAMS)),
        )

        call_count = 0

        def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                raise KeyboardInterrupt()

        monkeypatch.setattr(limiter_module, "sleep", mock_sleep)

        with pytest.raises(KeyboardInterrupt):
            limiter_module.main()

        # Defaults "0" -> mbps_to_bps("0") -> -1
        # This verifies the function runs with default env var values
        mock_client_cls.assert_called_once()
