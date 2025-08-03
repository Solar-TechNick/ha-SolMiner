"""Sensor platform for SolMiner."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfFrequency,
    UnitOfElectricCurrent,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolMinerCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = [
    # Mining performance sensors
    SensorEntityDescription(
        key="hashrate_5s",
        name="Hashrate (5s)",
        icon="mdi:speedometer",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.measurement,
    ),
    SensorEntityDescription(
        key="hashrate_1m",
        name="Hashrate (1m)",
        icon="mdi:speedometer",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.measurement,
    ),
    SensorEntityDescription(
        key="hashrate_15m",
        name="Hashrate (15m)",
        icon="mdi:speedometer",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.measurement,
    ),
    # Power sensors
    SensorEntityDescription(
        key="power_consumption",
        name="Power Consumption",
        device_class=SensorDeviceClass.power,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.measurement,
    ),
    SensorEntityDescription(
        key="efficiency",
        name="Power Efficiency",
        icon="mdi:flash",
        native_unit_of_measurement="W/TH",
        state_class=SensorStateClass.measurement,
    ),
    # Temperature sensors
    SensorEntityDescription(
        key="temp_avg",
        name="Average Temperature",
        device_class=SensorDeviceClass.temperature,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.measurement,
    ),
    SensorEntityDescription(
        key="temp_max",
        name="Maximum Temperature",
        device_class=SensorDeviceClass.temperature,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.measurement,
    ),
    # Board-specific sensors
    SensorEntityDescription(
        key="board_0_temp",
        name="Board 0 Temperature",
        device_class=SensorDeviceClass.temperature,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.measurement,
    ),
    SensorEntityDescription(
        key="board_1_temp",
        name="Board 1 Temperature",
        device_class=SensorDeviceClass.temperature,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.measurement,
    ),
    SensorEntityDescription(
        key="board_2_temp",
        name="Board 2 Temperature",
        device_class=SensorDeviceClass.temperature,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.measurement,
    ),
    # Fan sensors
    SensorEntityDescription(
        key="fan_speed_1",
        name="Fan 1 Speed",
        icon="mdi:fan",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.measurement,
    ),
    SensorEntityDescription(
        key="fan_speed_2",
        name="Fan 2 Speed",
        icon="mdi:fan",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.measurement,
    ),
    # Frequency and voltage sensors
    SensorEntityDescription(
        key="frequency",
        name="Chip Frequency",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.measurement,
    ),
    SensorEntityDescription(
        key="voltage",
        name="Board Voltage",
        device_class=SensorDeviceClass.voltage,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.measurement,
    ),
    # Solar sensors
    SensorEntityDescription(
        key="solar_power_available",
        name="Solar Power Available",
        device_class=SensorDeviceClass.power,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.measurement,
        icon="mdi:solar-power",
    ),
    SensorEntityDescription(
        key="solar_utilization",
        name="Solar Utilization",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.measurement,
        icon="mdi:solar-panel",
    ),
    # Status sensors
    SensorEntityDescription(
        key="status",
        name="Miner Status",
        icon="mdi:state-machine",
    ),
    SensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:clock-outline",
        native_unit_of_measurement="s",
        state_class=SensorStateClass.total_increasing,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolMiner sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    for description in SENSOR_DESCRIPTIONS:
        entities.append(SolMinerSensor(coordinator, description))
    
    async_add_entities(entities)


class SolMinerSensor(CoordinatorEntity, SensorEntity):
    """SolMiner sensor entity."""

    def __init__(
        self,
        coordinator: SolMinerCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        data = self.coordinator.data
        key = self.entity_description.key
        
        try:
            # Extract values based on sensor type
            if key == "hashrate_5s":
                return self._extract_hashrate(data.get("summary", {}), "5s")
            elif key == "hashrate_1m":
                return self._extract_hashrate(data.get("summary", {}), "1m")
            elif key == "hashrate_15m":
                return self._extract_hashrate(data.get("summary", {}), "15m")
            elif key == "power_consumption":
                return self._extract_power_consumption(data.get("stats", {}))
            elif key == "efficiency":
                return self._calculate_efficiency(data)
            elif key == "temp_avg":
                return self._extract_avg_temperature(data.get("stats", {}))
            elif key == "temp_max":
                return self._extract_max_temperature(data.get("stats", {}))
            elif key.startswith("board_") and key.endswith("_temp"):
                board_id = int(key.split("_")[1])
                return self._extract_board_temperature(data.get("devs", {}), board_id)
            elif key.startswith("fan_speed_"):
                fan_id = int(key.split("_")[2])
                return self._extract_fan_speed(data.get("stats", {}), fan_id)
            elif key == "frequency":
                return self._extract_frequency(data.get("frequency", {}))
            elif key == "voltage":
                return self._extract_voltage(data.get("stats", {}))
            elif key == "solar_power_available":
                return data.get("solar_power", 0)
            elif key == "solar_utilization":
                return self._calculate_solar_utilization(data)
            elif key == "status":
                return self._extract_status(data.get("summary", {}))
            elif key == "uptime":
                return self._extract_uptime(data.get("stats", {}))
                
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.debug("Error extracting sensor data for %s: %s", key, err)
            return None
        
        return None

    def _extract_hashrate(self, summary: Dict[str, Any], period: str) -> Optional[float]:
        """Extract hashrate for specific period."""
        if "SUMMARY" in summary:
            summary_data = summary["SUMMARY"][0]
            if period == "5s":
                return summary_data.get("MHS 5s", 0) / 1_000_000  # Convert to TH/s
            elif period == "1m":
                return summary_data.get("MHS 1m", 0) / 1_000_000
            elif period == "15m":
                return summary_data.get("MHS 15m", 0) / 1_000_000
        return None

    def _extract_power_consumption(self, stats: Dict[str, Any]) -> Optional[float]:
        """Extract power consumption."""
        if "STATS" in stats and len(stats["STATS"]) > 1:
            miner_stats = stats["STATS"][1]
            return miner_stats.get("Power", 0)
        return None

    def _calculate_efficiency(self, data: Dict[str, Any]) -> Optional[float]:
        """Calculate power efficiency (W/TH)."""
        power = self._extract_power_consumption(data.get("stats", {}))
        hashrate = self._extract_hashrate(data.get("summary", {}), "5s")
        
        if power and hashrate and hashrate > 0:
            return round(power / hashrate, 2)
        return None

    def _extract_avg_temperature(self, stats: Dict[str, Any]) -> Optional[float]:
        """Extract average temperature."""
        if "STATS" in stats and len(stats["STATS"]) > 1:
            miner_stats = stats["STATS"][1]
            return miner_stats.get("temp_avg", 0)
        return None

    def _extract_max_temperature(self, stats: Dict[str, Any]) -> Optional[float]:
        """Extract maximum temperature."""
        if "STATS" in stats and len(stats["STATS"]) > 1:
            miner_stats = stats["STATS"][1]
            return miner_stats.get("temp_max", 0)
        return None

    def _extract_board_temperature(self, devs: Dict[str, Any], board_id: int) -> Optional[float]:
        """Extract temperature for specific board."""
        if "DEVS" in devs and len(devs["DEVS"]) > board_id:
            board_data = devs["DEVS"][board_id]
            return board_data.get("Temperature", 0)
        return None

    def _extract_fan_speed(self, stats: Dict[str, Any], fan_id: int) -> Optional[int]:
        """Extract fan speed."""
        if "STATS" in stats and len(stats["STATS"]) > 1:
            miner_stats = stats["STATS"][1]
            return miner_stats.get(f"fan{fan_id}", 0)
        return None

    def _extract_frequency(self, frequency: Dict[str, Any]) -> Optional[float]:
        """Extract chip frequency."""
        if "frequency" in frequency:
            return frequency["frequency"]
        return None

    def _extract_voltage(self, stats: Dict[str, Any]) -> Optional[float]:
        """Extract board voltage."""
        if "STATS" in stats and len(stats["STATS"]) > 1:
            miner_stats = stats["STATS"][1]
            return miner_stats.get("voltage", 0)
        return None

    def _calculate_solar_utilization(self, data: Dict[str, Any]) -> Optional[float]:
        """Calculate solar power utilization percentage."""
        solar_power = data.get("solar_power", 0)
        power_consumption = self._extract_power_consumption(data.get("stats", {}))
        
        if solar_power > 0 and power_consumption:
            utilization = (power_consumption / solar_power) * 100
            return min(round(utilization, 1), 100)
        return 0

    def _extract_status(self, summary: Dict[str, Any]) -> Optional[str]:
        """Extract miner status."""
        if "SUMMARY" in summary:
            summary_data = summary["SUMMARY"][0]
            return summary_data.get("Status", "Unknown")
        return None

    def _extract_uptime(self, stats: Dict[str, Any]) -> Optional[int]:
        """Extract uptime in seconds."""
        if "STATS" in stats and len(stats["STATS"]) > 0:
            cgminer_stats = stats["STATS"][0]
            return cgminer_stats.get("Elapsed", 0)
        return None