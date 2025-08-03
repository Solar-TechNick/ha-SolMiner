"""Tests for SolMiner coordinator."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.solminer.coordinator import SolMinerCoordinator
from custom_components.solminer.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, SOLAR_CURVE


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {
        CONF_HOST: "192.168.1.210",
        CONF_USERNAME: "root",
        CONF_PASSWORD: "root",
    }
    entry.options = {}
    return entry


@pytest.fixture
def coordinator(mock_hass, mock_config_entry):
    """Create a coordinator for testing."""
    return SolMinerCoordinator(mock_hass, mock_config_entry)


@pytest.mark.asyncio
async def test_coordinator_initialization(coordinator):
    """Test coordinator initialization."""
    assert coordinator.host == "192.168.1.210"
    assert coordinator.solar_power_input == 0
    assert coordinator.solar_curve_enabled is False
    assert coordinator.max_solar_power == 5000


@pytest.mark.asyncio
async def test_successful_data_update(coordinator):
    """Test successful data update."""
    mock_api_responses = {
        "summary": {"SUMMARY": [{"MHS 5s": 100000000, "Status": "Alive"}]},
        "stats": {"STATS": [{}, {"Power": 3000, "temp_avg": 65}]},
        "devs": {"DEVS": [{"Temperature": 60}, {"Temperature": 65}, {"Temperature": 62}]},
        "pools": {"POOLS": [{"POOL": 1, "Status": "Alive"}]},
        "profile": {"profile": "0"},
        "frequency": {"frequency": 600},
        "health": {"healthy": True}
    }
    
    with patch.object(coordinator.api, "get_summary", return_value=mock_api_responses["summary"]):
        with patch.object(coordinator.api, "get_stats", return_value=mock_api_responses["stats"]):
            with patch.object(coordinator.api, "get_devs", return_value=mock_api_responses["devs"]):
                with patch.object(coordinator.api, "get_pools", return_value=mock_api_responses["pools"]):
                    with patch.object(coordinator.api, "get_profile", return_value=mock_api_responses["profile"]):
                        with patch.object(coordinator.api, "get_frequency", return_value=mock_api_responses["frequency"]):
                            with patch.object(coordinator.api, "get_health_chip", return_value=mock_api_responses["health"]):
                                data = await coordinator._async_update_data()
                                
                                assert data["summary"] == mock_api_responses["summary"]
                                assert data["stats"] == mock_api_responses["stats"]
                                assert data["solar_power"] == 0  # Manual input
                                assert "last_update" in data


@pytest.mark.asyncio
async def test_solar_curve_calculation(coordinator):
    """Test solar curve power calculation."""
    coordinator.solar_curve_enabled = True
    coordinator.max_solar_power = 10000
    
    # Mock current time to 12:00 (noon) - should be 100% in SOLAR_CURVE
    with patch("custom_components.solminer.coordinator.datetime") as mock_datetime:
        mock_datetime.now.return_value = MagicMock()
        mock_datetime.now.return_value.hour = 12
        
        solar_power = coordinator._get_current_solar_power()
        expected_power = 10000 * (SOLAR_CURVE[12] / 100)  # 100% at noon
        assert solar_power == expected_power


@pytest.mark.asyncio
async def test_manual_solar_power_input(coordinator):
    """Test manual solar power input."""
    coordinator.solar_curve_enabled = False
    coordinator.solar_power_input = 2500
    
    solar_power = coordinator._get_current_solar_power()
    assert solar_power == 2500


@pytest.mark.asyncio
async def test_set_solar_power_input(coordinator):
    """Test setting solar power input."""
    with patch.object(coordinator, "async_request_refresh") as mock_refresh:
        await coordinator.set_solar_power_input(3000)
        assert coordinator.solar_power_input == 3000
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_set_solar_curve_enabled(coordinator):
    """Test enabling/disabling solar curve."""
    with patch.object(coordinator, "async_request_refresh") as mock_refresh:
        await coordinator.set_solar_curve_enabled(True)
        assert coordinator.solar_curve_enabled is True
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_pause_resume_mining(coordinator):
    """Test pause and resume mining operations."""
    with patch.object(coordinator.api, "pause_mining") as mock_pause:
        with patch.object(coordinator, "async_request_refresh") as mock_refresh:
            result = await coordinator.pause_mining()
            assert result is True
            mock_pause.assert_called_once()
            mock_refresh.assert_called_once()
    
    with patch.object(coordinator.api, "resume_mining") as mock_resume:
        with patch.object(coordinator, "async_request_refresh") as mock_refresh:
            result = await coordinator.resume_mining()
            assert result is True
            mock_resume.assert_called_once()
            mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_power_profile_management(coordinator):
    """Test power profile operations."""
    with patch.object(coordinator.api, "set_profile") as mock_set_profile:
        with patch.object(coordinator, "async_request_refresh") as mock_refresh:
            result = await coordinator.set_power_profile("+2")
            assert result is True
            mock_set_profile.assert_called_once_with("+2")
            mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_hashboard_control(coordinator):
    """Test hashboard enable/disable operations."""
    with patch.object(coordinator.api, "enable_board") as mock_enable:
        with patch.object(coordinator, "async_request_refresh") as mock_refresh:
            result = await coordinator.enable_board(0)
            assert result is True
            mock_enable.assert_called_once_with(0)
            mock_refresh.assert_called_once()
    
    with patch.object(coordinator.api, "disable_board") as mock_disable:
        with patch.object(coordinator, "async_request_refresh") as mock_refresh:
            result = await coordinator.disable_board(1)
            assert result is True
            mock_disable.assert_called_once_with(1)
            mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_emergency_stop(coordinator):
    """Test emergency stop functionality."""
    with patch.object(coordinator.api, "pause_mining") as mock_pause:
        with patch.object(coordinator.api, "curtail_power") as mock_curtail:
            with patch.object(coordinator, "async_request_refresh") as mock_refresh:
                result = await coordinator.emergency_stop()
                assert result is True
                mock_pause.assert_called_once()
                mock_curtail.assert_called_once_with(0)
                mock_refresh.assert_called_once()


@pytest.mark.asyncio 
async def test_reboot_miner(coordinator):
    """Test miner reboot functionality."""
    with patch.object(coordinator.api, "reboot_device") as mock_reboot:
        result = await coordinator.reboot_miner()
        assert result is True
        mock_reboot.assert_called_once()


@pytest.mark.asyncio
async def test_api_error_handling(coordinator):
    """Test handling of API errors during data update."""
    from custom_components.solminer.luxos_api import LuxOSAPIError
    
    with patch.object(coordinator.api, "get_summary", side_effect=LuxOSAPIError("Connection failed")):
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()
        assert "Error communicating with miner" in str(exc_info.value)


@pytest.mark.asyncio
async def test_unexpected_error_handling(coordinator):
    """Test handling of unexpected errors during data update."""
    with patch.object(coordinator.api, "get_summary", side_effect=Exception("Unexpected error")):
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()
        assert "Unexpected error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_api_failure_in_operations(coordinator):
    """Test handling of API failures in coordinator operations."""
    from custom_components.solminer.luxos_api import LuxOSAPIError
    
    with patch.object(coordinator.api, "pause_mining", side_effect=LuxOSAPIError("API Error")):
        result = await coordinator.pause_mining()
        assert result is False


@pytest.mark.asyncio
async def test_coordinator_shutdown(coordinator):
    """Test coordinator shutdown process."""
    with patch.object(coordinator.api, "close") as mock_close:
        await coordinator.async_shutdown()
        mock_close.assert_called_once()