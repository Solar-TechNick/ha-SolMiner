"""Select platform for SolMiner."""
from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, POWER_PROFILES, POWER_MODES
from .coordinator import SolMinerCoordinator

_LOGGER = logging.getLogger(__name__)

SELECT_DESCRIPTIONS = [
    # Power profile selection
    SelectEntityDescription(
        key="power_profile",
        name="Power Profile",
        icon="mdi:lightning-bolt-circle",
        options=list(POWER_PROFILES.keys()),
    ),
    # Quick power modes
    SelectEntityDescription(
        key="power_mode",
        name="Power Mode",
        icon="mdi:flash",
        options=list(POWER_MODES.keys()),
    ),
    # Manual frequency profiles (-16 to +4)
    SelectEntityDescription(
        key="frequency_profile",
        name="Frequency Profile",
        icon="mdi:tune",
        options=[
            "-16", "-15", "-14", "-13", "-12", "-11", "-10", "-9",
            "-8", "-7", "-6", "-5", "-4", "-3", "-2", "-1",
            "0", "+1", "+2", "+3", "+4"
        ],
    ),
    # Mining pool selection (if multiple pools configured)
    SelectEntityDescription(
        key="active_pool",
        name="Active Mining Pool",
        icon="mdi:server-network",
        options=["pool_1", "pool_2", "pool_3"],  # Will be dynamically updated
    ),
    # Operating mode selection
    SelectEntityDescription(
        key="operating_mode",
        name="Operating Mode",
        icon="mdi:cog",
        options=[
            "normal",
            "solar_optimized", 
            "night_quiet",
            "eco_mode",
            "max_performance",
            "standby"
        ],
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolMiner select entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    for description in SELECT_DESCRIPTIONS:
        entities.append(SolMinerSelect(coordinator, description))
    
    async_add_entities(entities)


class SolMinerSelect(CoordinatorEntity, SelectEntity):
    """SolMiner select entity."""

    def __init__(
        self,
        coordinator: SolMinerCoordinator,
        description: SelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
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
    def current_option(self) -> Optional[str]:
        """Return the currently selected option."""
        if not self.coordinator.data:
            return None
            
        data = self.coordinator.data
        key = self.entity_description.key
        
        try:
            if key == "power_profile":
                profile_data = data.get("profile", {})
                current_profile = profile_data.get("profile", "0")
                # Map profile value back to friendly name
                for name, value in POWER_PROFILES.items():
                    if value == current_profile:
                        return name
                return "balanced"  # Default
                
            elif key == "power_mode":
                # Determine current mode based on power settings
                return getattr(self.coordinator, "current_power_mode", "balanced")
                
            elif key == "frequency_profile":
                profile_data = data.get("profile", {})
                return profile_data.get("profile", "0")
                
            elif key == "active_pool":
                pools_data = data.get("pools", {})
                if "POOLS" in pools_data:
                    for pool in pools_data["POOLS"]:
                        if pool.get("Status") == "Alive":
                            return f"pool_{pool.get('POOL', 1)}"
                return "pool_1"
                
            elif key == "operating_mode":
                return getattr(self.coordinator, "operating_mode", "normal")
                
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.debug("Error getting select option for %s: %s", key, err)
            return None
        
        return None

    @property
    def options(self) -> list[str]:
        """Return available options."""
        key = self.entity_description.key
        
        if key == "active_pool":
            # Dynamically get available pools
            if self.coordinator.data:
                pools_data = self.coordinator.data.get("pools", {})
                if "POOLS" in pools_data:
                    pool_options = []
                    for pool in pools_data["POOLS"]:
                        pool_id = pool.get("POOL", 1)
                        pool_options.append(f"pool_{pool_id}")
                    return pool_options if pool_options else ["pool_1"]
        
        return self.entity_description.options

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        key = self.entity_description.key
        
        try:
            if key == "power_profile":
                if option in POWER_PROFILES:
                    profile_value = POWER_PROFILES[option]
                    if profile_value != "manual":
                        await self.coordinator.set_power_profile(profile_value)
                        
            elif key == "power_mode":
                setattr(self.coordinator, "current_power_mode", option)
                if option == "solar_max":
                    await self.coordinator.set_power_limit(POWER_MODES[option])
                elif option == "eco_mode":
                    await self.coordinator.set_power_limit(POWER_MODES[option])
                elif option == "night_30":
                    # Set to 30% power
                    await self.coordinator.api.curtail_power(POWER_MODES[option])
                elif option == "night_15":
                    # Set to 15% power
                    await self.coordinator.api.curtail_power(POWER_MODES[option])
                elif option == "standby":
                    await self.coordinator.pause_mining()
                    
            elif key == "frequency_profile":
                await self.coordinator.set_power_profile(option)
                
            elif key == "active_pool":
                pool_id = int(option.split("_")[1])
                # Switch to specified pool (this would need pool management API)
                _LOGGER.info("Switching to pool %d", pool_id)
                
            elif key == "operating_mode":
                setattr(self.coordinator, "operating_mode", option)
                await self._apply_operating_mode(option)
                
        except Exception as err:
            _LOGGER.error("Error selecting option %s for %s: %s", option, key, err)

    async def _apply_operating_mode(self, mode: str) -> None:
        """Apply the selected operating mode."""
        if mode == "normal":
            await self.coordinator.set_power_profile("0")  # Balanced
        elif mode == "solar_optimized":
            await self.coordinator.set_solar_curve_enabled(True)
            setattr(self.coordinator, "auto_power_management", True)
        elif mode == "night_quiet":
            await self.coordinator.api.curtail_power(0.3)  # 30% power
        elif mode == "eco_mode":
            await self.coordinator.set_power_profile("-2")  # Ultra eco
        elif mode == "max_performance":
            await self.coordinator.set_power_profile("+2")  # Max power
        elif mode == "standby":
            await self.coordinator.pause_mining()
            
        await self.coordinator.async_request_refresh()