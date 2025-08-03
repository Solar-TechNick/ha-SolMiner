"""Tests for LuxOS API client."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp

from custom_components.solminer.luxos_api import LuxOSAPI, LuxOSAPIError


@pytest.fixture
def api_client():
    """Create a LuxOS API client for testing."""
    return LuxOSAPI("192.168.1.210", "root", "root")


@pytest.mark.asyncio
async def test_api_initialization(api_client):
    """Test API client initialization."""
    assert api_client.host == "192.168.1.210"
    assert api_client.username == "root"
    assert api_client.password == "root"
    assert api_client.session_id is None


@pytest.mark.asyncio
async def test_successful_logon(api_client):
    """Test successful authentication."""
    mock_response = {
        "session_id": "test_session_123"
    }
    
    with patch.object(api_client, "_send_command", return_value=mock_response):
        result = await api_client.logon()
        assert result is True
        assert api_client.session_id == "test_session_123"


@pytest.mark.asyncio
async def test_failed_logon(api_client):
    """Test failed authentication."""
    with patch.object(api_client, "_send_command", side_effect=LuxOSAPIError("Auth failed")):
        result = await api_client.logon()
        assert result is False
        assert api_client.session_id is None


@pytest.mark.asyncio
async def test_send_command_success(api_client):
    """Test successful command sending."""
    mock_response_data = {"result": "success", "data": {"hashrate": 100}}
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)
    
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    with patch.object(api_client, "_get_session", return_value=mock_session):
        result = await api_client._send_command("summary")
        assert result == mock_response_data
        mock_session.post.assert_called_once()


@pytest.mark.asyncio
async def test_send_command_http_error(api_client):
    """Test HTTP error handling."""
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    with patch.object(api_client, "_get_session", return_value=mock_session):
        with pytest.raises(LuxOSAPIError) as exc_info:
            await api_client._send_command("summary")
        assert "HTTP 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_command_api_error(api_client):
    """Test API error response handling."""
    mock_response_data = {"error": "Invalid command"}
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)
    
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    with patch.object(api_client, "_get_session", return_value=mock_session):
        with pytest.raises(LuxOSAPIError) as exc_info:
            await api_client._send_command("invalid")
        assert "API Error: Invalid command" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pause_resume_mining(api_client):
    """Test pause and resume mining operations."""
    api_client.session_id = "test_session"
    
    with patch.object(api_client, "_send_command", return_value={"result": "ok"}) as mock_send:
        # Test pause
        await api_client.pause_mining()
        mock_send.assert_called_with("pause")
        
        # Test resume
        await api_client.resume_mining()
        mock_send.assert_called_with("resume")


@pytest.mark.asyncio
async def test_board_control(api_client):
    """Test hashboard enable/disable operations."""
    api_client.session_id = "test_session"
    
    with patch.object(api_client, "_send_command", return_value={"result": "ok"}) as mock_send:
        # Test enable board
        await api_client.enable_board(0)
        mock_send.assert_called_with("enableboard", "0")
        
        # Test disable board
        await api_client.disable_board(1)
        mock_send.assert_called_with("disableboard", "1")


@pytest.mark.asyncio
async def test_power_management(api_client):
    """Test power management operations."""
    api_client.session_id = "test_session"
    
    with patch.object(api_client, "_send_command", return_value={"result": "ok"}) as mock_send:
        # Test set power limit
        await api_client.set_power_limit(3000)
        mock_send.assert_called_with("power", "3000")
        
        # Test curtail power
        await api_client.curtail_power(0.8)
        mock_send.assert_called_with("curtail", "0.8")
        
        # Test set profile
        await api_client.set_profile("+2")
        mock_send.assert_called_with("profileset", "+2")


@pytest.mark.asyncio
async def test_auto_login_for_authenticated_commands(api_client):
    """Test automatic login for commands requiring authentication."""
    with patch.object(api_client, "logon", return_value=True) as mock_logon:
        with patch.object(api_client, "_send_command", return_value={"result": "ok"}):
            # Command requiring authentication should trigger login
            await api_client.pause_mining()
            mock_logon.assert_called_once()


@pytest.mark.asyncio
async def test_close_session(api_client):
    """Test session cleanup."""
    api_client.session_id = "test_session"
    mock_session = AsyncMock()
    api_client._session = mock_session
    
    with patch.object(api_client, "logoff") as mock_logoff:
        await api_client.close()
        mock_logoff.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_connection_timeout():
    """Test connection timeout handling."""
    api_client = LuxOSAPI("192.168.1.999")  # Non-existent IP
    
    with patch("aiohttp.ClientSession.post", side_effect=aiohttp.ClientError("Timeout")):
        with pytest.raises(LuxOSAPIError) as exc_info:
            await api_client.get_summary()
        assert "Connection error" in str(exc_info.value)