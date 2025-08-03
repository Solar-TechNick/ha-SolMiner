"""Switch platform for SolMiner."""
from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolMinerCoordinator

_LOGGER = logging.getLogger(__name__)

SWITCH_DESCRIPTIONS = [
    # Mining control switches
    SwitchEntityDescription(
        key="mining_enabled",
        name="Mining Enabled",
        icon="mdi:pickaxe",
    ),
    # Hashboard control switches
    SwitchEntityDescription(
        key="board_0_enabled",
        name="Board 0 Enabled",
        icon="mdi:chip",
    ),
    SwitchEntityDescription(
        key="board_1_enabled",
        name="Board 1 Enabled",
        icon="mdi:chip",
    ),
    SwitchEntityDescription(
        key="board_2_enabled",
        name="Board 2 Enabled",
        icon="mdi:chip",
    ),
    # Solar automation switches
    SwitchEntityDescription(
        key="solar_curve_enabled",
        name="Solar Curve Mode",
        icon="mdi:weather-sunny",
    ),
    SwitchEntityDescription(
        key="auto_power_management",
        name="Auto Power Management",
        icon="mdi:lightning-bolt-circle",
    ),
    # Temperature protection
    SwitchEntityDescription(
        key="temp_protection_enabled",
        name="Temperature Protection",
        icon="mdi:thermometer-alert",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolMiner switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    for description in SWITCH_DESCRIPTIONS:
        entities.append(SolMinerSwitch(coordinator, description))
    
    async_add_entities(entities)


class SolMinerSwitch(CoordinatorEntity, SwitchEntity):
    """SolMiner switch entity."""

    def __init__(
        self,
        coordinator: SolMinerCoordinator,
        description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Antminer {coordinator.host}",
            "manufacturer": "Bitmain",
            "model": "Antminer",
            "sw_version": "LuxOS",
        }

    @property
    def is_on(self) -> Optional[bool]:
        """Return the state of the switch."""
        if not self.coordinator.data:
            return None
            
        data = self.coordinator.data
        key = self.entity_description.key
        
        try:
            if key == "mining_enabled":
                return self._is_mining_enabled(data.get("summary", {}))
            elif key.startswith("board_") and key.endswith("_enabled"):
                board_id = int(key.split("_")[1])
                return self._is_board_enabled(data.get("devs", {}), board_id)
            elif key == "solar_curve_enabled":
                return data.get("solar_curve_enabled", False)
            elif key == "auto_power_management":
                # This would be stored in coordinator state
                return getattr(self.coordinator, "auto_power_management", False)
            elif key == "temp_protection_enabled":
                # This would be stored in coordinator state
                return getattr(self.coordinator, "temp_protection_enabled", True)
                
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.debug("Error getting switch state for %s: %s", key, err)
            return None
        
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        key = self.entity_description.key
        
        try:
            if key == "mining_enabled":
                await self.coordinator.resume_mining()
            elif key.startswith("board_") and key.endswith("_enabled"):
                board_id = int(key.split("_")[1])
                await self.coordinator.enable_board(board_id)
            elif key == "solar_curve_enabled":
                await self.coordinator.set_solar_curve_enabled(True)
            elif key == "auto_power_management":
                # Set coordinator state and enable auto management
                setattr(self.coordinator, "auto_power_management", True)
                await self.coordinator.async_request_refresh()
            elif key == "temp_protection_enabled":
                # Enable temperature protection
                setattr(self.coordinator, "temp_protection_enabled", True)
                await self.coordinator.async_request_refresh()
                
        except Exception as err:
            _LOGGER.error("Error turning on switch %s: %s", key, err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        key = self.entity_description.key
        
        try:
            if key == "mining_enabled":
                await self.coordinator.pause_mining()
            elif key.startswith("board_") and key.endswith("_enabled"):
                board_id = int(key.split("_")[1])
                await self.coordinator.disable_board(board_id)
            elif key == "solar_curve_enabled":
                await self.coordinator.set_solar_curve_enabled(False)
            elif key == "auto_power_management":
                # Disable auto management
                setattr(self.coordinator, "auto_power_management", False)
                await self.coordinator.async_request_refresh()
            elif key == "temp_protection_enabled":
                # Disable temperature protection
                setattr(self.coordinator, "temp_protection_enabled", False)
                await self.coordinator.async_request_refresh()
                
        except Exception as err:
            _LOGGER.error("Error turning off switch %s: %s", key, err)

    def _is_mining_enabled(self, summary: dict) -> Optional[bool]:
        """Check if mining is enabled."""
        if "SUMMARY" in summary:
            summary_data = summary["SUMMARY"][0]
            status = summary_data.get("Status", "").lower()
            return "alive" in status and "work" in status
        return None

    def _is_board_enabled(self, devs: dict, board_id: int) -> Optional[bool]:
        """Check if specific board is enabled."""
        if "DEVS" in devs and len(devs["DEVS"]) > board_id:
            board_data = devs["DEVS"][board_id]
            status = board_data.get("Status", "").lower()
            return "alive" in status
        return None