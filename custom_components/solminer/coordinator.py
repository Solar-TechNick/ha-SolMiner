"""Data update coordinator for SolMiner."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, SOLAR_CURVE
from .luxos_api import LuxOSAPI, LuxOSAPIError

_LOGGER = logging.getLogger(__name__)


class SolMinerCoordinator(DataUpdateCoordinator):
    """Data coordinator for SolMiner."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        username = entry.data.get(CONF_USERNAME, "root")
        password = entry.data.get(CONF_PASSWORD, "root")
        
        self.api = LuxOSAPI(self.host, username, password)
        
        # Solar simulation data
        self.solar_power_input = 0  # Manual solar power input
        self.solar_curve_enabled = False
        self.max_solar_power = 5000  # Maximum solar power for curve simulation
        
        update_interval = timedelta(
            seconds=entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
        )
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the miner."""
        try:
            # Get basic miner data
            summary = await self.api.get_summary()
            stats = await self.api.get_stats()
            devs = await self.api.get_devs()
            pools = await self.api.get_pools()
            profile = await self.api.get_profile()
            frequency = await self.api.get_frequency()
            health = await self.api.get_health_chip()
            
            # Calculate solar curve value if enabled
            current_solar_power = self._get_current_solar_power()
            
            return {
                "summary": summary,
                "stats": stats,
                "devs": devs,
                "pools": pools,
                "profile": profile,
                "frequency": frequency,
                "health": health,
                "solar_power": current_solar_power,
                "solar_power_input": self.solar_power_input,
                "solar_curve_enabled": self.solar_curve_enabled,
                "max_solar_power": self.max_solar_power,
                "last_update": datetime.now(),
            }
            
        except LuxOSAPIError as err:
            raise UpdateFailed(f"Error communicating with miner: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}")

    def _get_current_solar_power(self) -> float:
        """Get current solar power based on input method."""
        if self.solar_curve_enabled:
            # Use simulated solar curve
            hour = datetime.now().hour
            curve_percentage = SOLAR_CURVE[hour] / 100
            return self.max_solar_power * curve_percentage
        else:
            # Use manual input
            return self.solar_power_input

    async def set_solar_power_input(self, power: float) -> None:
        """Set manual solar power input."""
        self.solar_power_input = power
        await self.async_request_refresh()

    async def set_solar_curve_enabled(self, enabled: bool) -> None:
        """Enable/disable solar curve simulation."""
        self.solar_curve_enabled = enabled
        await self.async_request_refresh()

    async def set_max_solar_power(self, power: float) -> None:
        """Set maximum solar power for curve simulation."""
        self.max_solar_power = power
        await self.async_request_refresh()

    async def pause_mining(self) -> bool:
        """Pause mining operations."""
        try:
            await self.api.pause_mining()
            await self.async_request_refresh()
            return True
        except LuxOSAPIError as err:
            _LOGGER.error("Failed to pause mining: %s", err)
            return False

    async def resume_mining(self) -> bool:
        """Resume mining operations."""
        try:
            await self.api.resume_mining()
            await self.async_request_refresh()
            return True
        except LuxOSAPIError as err:
            _LOGGER.error("Failed to resume mining: %s", err)
            return False

    async def set_power_profile(self, profile: str) -> bool:
        """Set power profile."""
        try:
            await self.api.set_profile(profile)
            await self.async_request_refresh()
            return True
        except LuxOSAPIError as err:
            _LOGGER.error("Failed to set power profile: %s", err)
            return False

    async def set_power_limit(self, watts: int) -> bool:
        """Set power limit."""
        try:
            await self.api.set_power_limit(watts)
            await self.async_request_refresh()
            return True
        except LuxOSAPIError as err:
            _LOGGER.error("Failed to set power limit: %s", err)
            return False

    async def enable_board(self, board_id: int) -> bool:
        """Enable hashboard."""
        try:
            await self.api.enable_board(board_id)
            await self.async_request_refresh()
            return True
        except LuxOSAPIError as err:
            _LOGGER.error("Failed to enable board %d: %s", board_id, err)
            return False

    async def disable_board(self, board_id: int) -> bool:
        """Disable hashboard."""
        try:
            await self.api.disable_board(board_id)
            await self.async_request_refresh()
            return True
        except LuxOSAPIError as err:
            _LOGGER.error("Failed to disable board %d: %s", board_id, err)
            return False

    async def reboot_miner(self) -> bool:
        """Reboot the miner."""
        try:
            await self.api.reboot_device()
            return True
        except LuxOSAPIError as err:
            _LOGGER.error("Failed to reboot miner: %s", err)
            return False

    async def emergency_stop(self) -> bool:
        """Emergency stop - pause mining and set minimum power."""
        try:
            await self.api.pause_mining()
            await self.api.curtail_power(0)
            await self.async_request_refresh()
            return True
        except LuxOSAPIError as err:
            _LOGGER.error("Failed to emergency stop: %s", err)
            return False

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.api.close()