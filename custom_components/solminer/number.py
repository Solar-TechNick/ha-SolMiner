"""Number platform for SolMiner."""
from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolMinerCoordinator

_LOGGER = logging.getLogger(__name__)

NUMBER_DESCRIPTIONS = [
    # Power management numbers
    NumberEntityDescription(
        key="solar_power_input",
        name="Solar Power Input",
        icon="mdi:solar-power",
        native_min_value=0,
        native_max_value=50000,
        native_step=100,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    NumberEntityDescription(
        key="max_solar_power",
        name="Max Solar Power",
        icon="mdi:solar-panel",
        native_min_value=1000,
        native_max_value=50000,
        native_step=500,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    NumberEntityDescription(
        key="power_limit",
        name="Power Limit",
        icon="mdi:lightning-bolt",
        native_min_value=500,
        native_max_value=5000,
        native_step=50,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    NumberEntityDescription(
        key="performance_scaling",
        name="Performance Scaling",
        icon="mdi:speedometer",
        native_min_value=50,
        native_max_value=130,
        native_step=5,
        native_unit_of_measurement="%",
    ),
    NumberEntityDescription(
        key="temperature_threshold",
        name="Temperature Threshold",
        icon="mdi:thermometer-alert",
        native_min_value=60,
        native_max_value=85,
        native_step=1,
        native_unit_of_measurement="°C",
    ),
    NumberEntityDescription(
        key="fan_speed_override",
        name="Fan Speed Override",
        icon="mdi:fan",
        native_min_value=0,
        native_max_value=100,
        native_step=5,
        native_unit_of_measurement="%",
    ),
    NumberEntityDescription(
        key="chip_frequency",
        name="Chip Frequency",
        icon="mdi:sine-wave",
        native_min_value=400,
        native_max_value=800,
        native_step=25,
        native_unit_of_measurement="MHz",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolMiner number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    for description in NUMBER_DESCRIPTIONS:
        entities.append(SolMinerNumber(coordinator, description))
    
    async_add_entities(entities)


class SolMinerNumber(CoordinatorEntity, NumberEntity):
    """SolMiner number entity."""

    def __init__(
        self,
        coordinator: SolMinerCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
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
    def native_value(self) -> Optional[float]:
        """Return the current value."""
        if not self.coordinator.data:
            return None
            
        data = self.coordinator.data
        key = self.entity_description.key
        
        try:
            if key == "solar_power_input":
                return data.get("solar_power_input", 0)
            elif key == "max_solar_power":
                return data.get("max_solar_power", 5000)
            elif key == "power_limit":
                return getattr(self.coordinator, "power_limit", 3000)
            elif key == "performance_scaling":
                return getattr(self.coordinator, "performance_scaling", 100)
            elif key == "temperature_threshold":
                return getattr(self.coordinator, "temperature_threshold", 75)
            elif key == "fan_speed_override":
                return getattr(self.coordinator, "fan_speed_override", 0)
            elif key == "chip_frequency":
                freq_data = data.get("frequency", {})
                if "frequency" in freq_data:
                    return freq_data["frequency"]
                return 600  # Default frequency
                
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.debug("Error getting number value for %s: %s", key, err)
            return None
        
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        key = self.entity_description.key
        
        try:
            if key == "solar_power_input":
                await self.coordinator.set_solar_power_input(value)
            elif key == "max_solar_power":
                await self.coordinator.set_max_solar_power(value)
            elif key == "power_limit":
                setattr(self.coordinator, "power_limit", value)
                await self.coordinator.set_power_limit(int(value))
            elif key == "performance_scaling":
                setattr(self.coordinator, "performance_scaling", value)
                # Convert percentage to profile adjustment
                if value == 100:
                    profile = "0"  # Balanced
                elif value > 100:
                    # Scale to +1 to +4 range
                    adjustment = min(4, int((value - 100) / 7.5))
                    profile = f"+{adjustment}"
                else:
                    # Scale to -1 to -16 range
                    adjustment = max(-16, int((value - 100) / 3.125))
                    profile = str(adjustment)
                await self.coordinator.set_power_profile(profile)
            elif key == "temperature_threshold":
                setattr(self.coordinator, "temperature_threshold", value)
                await self.coordinator.async_request_refresh()
            elif key == "fan_speed_override":
                setattr(self.coordinator, "fan_speed_override", value)
                if value > 0:
                    fan_speed = int((value / 100) * 5000)  # Convert % to RPM
                    await self.coordinator.api.set_fan_speed(fan_speed)
                await self.coordinator.async_request_refresh()
            elif key == "chip_frequency":
                await self.coordinator.api.set_frequency(int(value))
                await self.coordinator.async_request_refresh()
                
        except Exception as err:
            _LOGGER.error("Error setting number value for %s: %s", key, err)