"""The SolMiner integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import DeviceInfo
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import DOMAIN
from .coordinator import SolMinerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SolMiner from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = SolMinerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _async_setup_services(hass)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    
    return unload_ok


async def _async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for SolMiner."""
    
    async def emergency_stop_service(call: ServiceCall) -> None:
        """Handle emergency stop service call."""
        device_id = call.data.get("device_id")
        coordinator = _get_coordinator_from_device(hass, device_id)
        if coordinator:
            await coordinator.emergency_stop()
    
    async def reboot_miner_service(call: ServiceCall) -> None:
        """Handle reboot miner service call."""
        device_id = call.data.get("device_id")
        coordinator = _get_coordinator_from_device(hass, device_id)
        if coordinator:
            await coordinator.reboot_miner()
    
    async def set_solar_mode_service(call: ServiceCall) -> None:
        """Handle set solar mode service call."""
        device_id = call.data.get("device_id")
        max_power = call.data.get("max_power", 4200)
        coordinator = _get_coordinator_from_device(hass, device_id)
        if coordinator:
            await coordinator.set_power_limit(max_power)
            await coordinator.set_solar_curve_enabled(True)
    
    async def set_night_mode_service(call: ServiceCall) -> None:
        """Handle set night mode service call."""
        device_id = call.data.get("device_id")
        power_percentage = call.data.get("power_percentage", 30) / 100
        coordinator = _get_coordinator_from_device(hass, device_id)
        if coordinator:
            await coordinator.api.curtail_power(power_percentage)
    
    async def apply_power_profile_service(call: ServiceCall) -> None:
        """Handle apply power profile service call."""
        device_id = call.data.get("device_id")
        profile = call.data.get("profile", "0")
        coordinator = _get_coordinator_from_device(hass, device_id)
        if coordinator:
            await coordinator.set_power_profile(profile)
    
    async def control_hashboard_service(call: ServiceCall) -> None:
        """Handle control hashboard service call."""
        device_id = call.data.get("device_id")
        board_id = call.data.get("board_id", 0)
        enabled = call.data.get("enabled", True)
        coordinator = _get_coordinator_from_device(hass, device_id)
        if coordinator:
            if enabled:
                await coordinator.enable_board(board_id)
            else:
                await coordinator.disable_board(board_id)
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        "emergency_stop",
        emergency_stop_service,
        schema=vol.Schema({}),
    )
    
    hass.services.async_register(
        DOMAIN,
        "reboot_miner", 
        reboot_miner_service,
        schema=vol.Schema({}),
    )
    
    hass.services.async_register(
        DOMAIN,
        "set_solar_mode",
        set_solar_mode_service,
        schema=vol.Schema({
            vol.Required("max_power"): cv.positive_int,
        }),
    )
    
    hass.services.async_register(
        DOMAIN,
        "set_night_mode",
        set_night_mode_service,
        schema=vol.Schema({
            vol.Required("power_percentage"): vol.All(vol.Coerce(int), vol.Range(min=0, max=50)),
        }),
    )
    
    hass.services.async_register(
        DOMAIN,
        "apply_power_profile",
        apply_power_profile_service,
        schema=vol.Schema({
            vol.Required("profile"): cv.string,
        }),
    )
    
    hass.services.async_register(
        DOMAIN,
        "control_hashboard",
        control_hashboard_service,
        schema=vol.Schema({
            vol.Required("board_id"): vol.All(vol.Coerce(int), vol.Range(min=0, max=2)),
            vol.Required("enabled"): cv.boolean,
        }),
    )


def _get_coordinator_from_device(hass: HomeAssistant, device_id: str) -> SolMinerCoordinator:
    """Get coordinator from device ID."""
    # This is a simplified implementation - in practice you'd need to map device_id to coordinator
    coordinators = hass.data.get(DOMAIN, {})
    if coordinators:
        return next(iter(coordinators.values()))
    return None