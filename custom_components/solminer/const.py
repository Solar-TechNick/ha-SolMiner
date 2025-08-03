"""Constants for the SolMiner integration."""
from __future__ import annotations

DOMAIN = "solminer"

# Configuration constants
CONF_HOST = "host"
CONF_USERNAME = "username" 
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"

# Default values
DEFAULT_USERNAME = "root"
DEFAULT_PASSWORD = "root"
DEFAULT_UPDATE_INTERVAL = 30

# Common credential combinations for LuxOS/Antminer devices
COMMON_CREDENTIALS = [
    ("root", "root"),      # Most common
    ("admin", "admin"),    # Alternative admin
    ("", "root"),          # No username, root password
    ("root", ""),          # Root username, no password
    ("admin", ""),         # Admin username, no password  
    ("", "admin"),         # No username, admin password
    ("", ""),              # No credentials at all
]

# Power profiles
POWER_PROFILES = {
    "max_power": "+2",
    "balanced": "0", 
    "ultra_eco": "-2",
    "manual": "manual"
}

# Predefined power modes
POWER_MODES = {
    "solar_max": 4200,
    "eco_mode": 1500,
    "night_30": 0.3,
    "night_15": 0.15,
    "standby": 0
}

# Solar curve simulation (24-hour power percentages)
SOLAR_CURVE = [
    0, 0, 0, 0, 0, 0,  # 00:00-05:00 - Night
    5, 15, 30, 50, 70, 85,  # 06:00-11:00 - Morning
    100, 95, 85, 70, 50, 30,  # 12:00-17:00 - Afternoon  
    15, 5, 0, 0, 0, 0  # 18:00-23:00 - Evening
]