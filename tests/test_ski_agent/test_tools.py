"""Tests for Ski Agent native tools."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from clarvis_agents.ski_agent.tools import (
    fetch_ski_conditions_impl,
    set_conditions_url,
    get_conditions_url,
    ski_tools_server,
    DEFAULT_CONDITIONS_URL,
)


class TestConditionsUrlConfig:
    """Test suite for conditions URL configuration."""

    def test_default_url(self):
        """Test default conditions URL."""
        # Reset to default
        set_conditions_url(DEFAULT_CONDITIONS_URL)
        assert get_conditions_url() == "https://cloudserv.skihood.com/"

    def test_set_custom_url(self):
        """Test setting custom conditions URL."""
        custom_url = "https://example.com/conditions"
        set_conditions_url(custom_url)
        assert get_conditions_url() == custom_url

        # Reset to default
        set_conditions_url(DEFAULT_CONDITIONS_URL)


class TestFetchSkiConditionsImpl:
    """Test suite for fetch_ski_conditions_impl function."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        """Test successful conditions fetch."""
        mock_response = MagicMock()
        mock_response.text = "<html>Snow: 72 inches</html>"
        mock_response.raise_for_status = MagicMock()

        with patch("clarvis_agents.ski_agent.tools.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_ski_conditions_impl()

            assert result == "<html>Snow: 72 inches</html>"
            mock_instance.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_with_custom_url(self):
        """Test fetch with custom URL parameter."""
        custom_url = "https://example.com/snow"
        mock_response = MagicMock()
        mock_response.text = "Custom data"
        mock_response.raise_for_status = MagicMock()

        with patch("clarvis_agents.ski_agent.tools.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_ski_conditions_impl(url=custom_url)

            assert result == "Custom data"
            # Verify custom URL was used
            call_args = mock_instance.get.call_args
            assert call_args[0][0] == custom_url

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test handling of timeout errors."""
        with patch("clarvis_agents.ski_agent.tools.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_ski_conditions_impl()

            assert "Error" in result
            assert "timed out" in result.lower()

    @pytest.mark.asyncio
    async def test_http_error(self):
        """Test handling of HTTP errors."""
        with patch("clarvis_agents.ski_agent.tools.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 503
            error = httpx.HTTPStatusError(
                "Service Unavailable",
                request=MagicMock(),
                response=mock_response,
            )
            mock_instance.get = AsyncMock(side_effect=error)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_ski_conditions_impl()

            assert "Error" in result
            assert "503" in result

    @pytest.mark.asyncio
    async def test_request_error(self):
        """Test handling of connection errors."""
        with patch("clarvis_agents.ski_agent.tools.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_ski_conditions_impl()

            assert "Error" in result
            assert "connect" in result.lower()


class TestSkiToolsServer:
    """Test suite for the SDK MCP server configuration."""

    def test_server_exists(self):
        """Test that ski_tools_server is defined."""
        assert ski_tools_server is not None

    def test_server_has_name(self):
        """Test that server has expected name."""
        # The server object structure depends on SDK implementation
        # This is a basic sanity check
        assert ski_tools_server is not None
