"""Tests for SolMiner config flow."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from custom_components.solminer.config_flow import ConfigFlow, CannotConnect, InvalidAuth
from custom_components.solminer.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def config_flow(mock_hass):
    """Create a config flow for testing."""
    flow = ConfigFlow()
    flow.hass = mock_hass
    return flow


@pytest.mark.asyncio
async def test_form_display(config_flow):
    """Test that initial form is displayed correctly."""
    result = await config_flow.async_step_user()
    
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_successful_config_creation(config_flow):
    """Test successful configuration creation."""
    user_input = {
        CONF_HOST: "192.168.1.210",
        CONF_USERNAME: "root", 
        CONF_PASSWORD: "root",
    }
    
    with patch("custom_components.solminer.config_flow.validate_input") as mock_validate:
        mock_validate.return_value = {"title": "SolMiner 192.168.1.210"}
        
        with patch.object(config_flow, "async_set_unique_id") as mock_set_unique_id:
            with patch.object(config_flow, "_abort_if_unique_id_configured") as mock_abort:
                result = await config_flow.async_step_user(user_input)
                
                assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
                assert result["title"] == "SolMiner 192.168.1.210"
                assert result["data"] == user_input
                
                mock_validate.assert_called_once_with(config_flow.hass, user_input)
                mock_set_unique_id.assert_called_once_with("192.168.1.210")


@pytest.mark.asyncio
async def test_cannot_connect_error(config_flow):
    """Test handling of connection errors."""
    user_input = {
        CONF_HOST: "192.168.1.999",  # Non-existent IP
        CONF_USERNAME: "root",
        CONF_PASSWORD: "root",
    }
    
    with patch("custom_components.solminer.config_flow.validate_input", side_effect=CannotConnect):
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_invalid_auth_error(config_flow):
    """Test handling of authentication errors."""
    user_input = {
        CONF_HOST: "192.168.1.210",
        CONF_USERNAME: "wrong",
        CONF_PASSWORD: "wrong",
    }
    
    with patch("custom_components.solminer.config_flow.validate_input", side_effect=InvalidAuth):
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_unknown_error(config_flow):
    """Test handling of unexpected errors."""
    user_input = {
        CONF_HOST: "192.168.1.210",
        CONF_USERNAME: "root",
        CONF_PASSWORD: "root",
    }
    
    with patch("custom_components.solminer.config_flow.validate_input", side_effect=Exception("Unexpected")):
        result = await config_flow.async_step_user(user_input)
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"]["base"] == "unknown"


@pytest.mark.asyncio
async def test_validate_input_success():
    """Test successful input validation."""
    from custom_components.solminer.config_flow import validate_input
    
    mock_hass = MagicMock()
    data = {
        CONF_HOST: "192.168.1.210",
        CONF_USERNAME: "root",
        CONF_PASSWORD: "root",
    }
    
    mock_api = AsyncMock()
    mock_api.get_version.return_value = {"version": "1.0"}
    mock_api.logon.return_value = True
    mock_api.logoff.return_value = None
    mock_api.close.return_value = None
    
    with patch("custom_components.solminer.config_flow.LuxOSAPI", return_value=mock_api):
        result = await validate_input(mock_hass, data)
        
        assert result["title"] == "SolMiner 192.168.1.210"
        mock_api.get_version.assert_called_once()
        mock_api.logon.assert_called_once()
        mock_api.logoff.assert_called_once()
        mock_api.close.assert_called_once()


@pytest.mark.asyncio
async def test_validate_input_connection_failure():
    """Test input validation with connection failure."""
    from custom_components.solminer.config_flow import validate_input
    from custom_components.solminer.luxos_api import LuxOSAPIError
    
    mock_hass = MagicMock()
    data = {
        CONF_HOST: "192.168.1.999",
        CONF_USERNAME: "root",
        CONF_PASSWORD: "root",
    }
    
    mock_api = AsyncMock()
    mock_api.get_version.side_effect = LuxOSAPIError("Connection failed")
    mock_api.close.return_value = None
    
    with patch("custom_components.solminer.config_flow.LuxOSAPI", return_value=mock_api):
        with pytest.raises(InvalidAuth):
            await validate_input(mock_hass, data)
        
        mock_api.close.assert_called_once()


@pytest.mark.asyncio
async def test_validate_input_without_auth():
    """Test input validation when authentication is not required."""
    from custom_components.solminer.config_flow import validate_input
    
    mock_hass = MagicMock()
    data = {
        CONF_HOST: "192.168.1.210",
        CONF_USERNAME: "root",
        CONF_PASSWORD: "root",
    }
    
    mock_api = AsyncMock()
    mock_api.get_version.return_value = {"version": "1.0"}
    mock_api.logon.return_value = False  # No auth required
    mock_api.close.return_value = None
    
    with patch("custom_components.solminer.config_flow.LuxOSAPI", return_value=mock_api):
        result = await validate_input(mock_hass, data)
        
        assert result["title"] == "SolMiner 192.168.1.210"
        mock_api.get_version.assert_called_once()
        mock_api.logon.assert_called_once()
        # logoff should not be called if login returned False
        mock_api.logoff.assert_not_called()


@pytest.mark.asyncio
async def test_default_form_values(config_flow):
    """Test that form displays default values correctly."""
    result = await config_flow.async_step_user()
    
    # Check that default values are present in the schema
    schema_keys = result["data_schema"].schema
    
    # Find the username and password fields and check their defaults
    for key, validator in schema_keys.items():
        if hasattr(key, 'schema') and key.schema == CONF_USERNAME:
            assert key.default() == "root"
        elif hasattr(key, 'schema') and key.schema == CONF_PASSWORD:
            assert key.default() == "root"