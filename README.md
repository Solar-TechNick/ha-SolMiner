# SolMiner - Home Assistant Integration

A comprehensive Home Assistant custom component for solar-powered Bitcoin mining operations using Antminer devices with LuxOS firmware.

## Features

### 🌞 Solar Power Integration
- **Manual Power Input**: Set available solar power (0-50000W)
- **Solar Curve Simulation**: Automatic power adjustment following sun patterns throughout the day
- **Solar Efficiency Monitoring**: Real-time visual feedback on solar power utilization
- **Peak Solar Mode**: Optimize mining during maximum sun availability

### ⚡ Mining Control
- **Pause/Resume**: Instantly disable/enable all hashboards
- **Solar Max Mode**: Set 4200W for maximum solar power utilization
- **Eco Mode**: Set 1500W for energy-efficient mining
- **Emergency Stop**: Immediate shutdown of all mining operations

### 🔧 Power Profiles
- **Max Power (+2)**: Overclock profile for peak performance
- **Balanced (0)**: Default profile for optimal efficiency
- **Ultra Eco (-2)**: Underclock profile for minimal power consumption
- **Manual Range**: -16 to +4 frequency adjustment

### 🎛️ Hashboard Control
- **Individual Board Toggle**: Control boards 0, 1, and 2 independently
- **Real-time Status**: Monitor temperature, frequency, voltage per board
- **Smart Automation**: Automatic board management based on solar power

### 📊 Real-time Monitoring
- **Auto-refresh**: Updates every 30-60 seconds (configurable)
- **Performance Metrics**: Hashrate (5s, 1m, 15m), power consumption, efficiency
- **Temperature Monitoring**: Per-board and overall temperature tracking
- **Fan Control**: Monitor and override fan speeds

### 🌙 Night Operations
- **Night Mode (30%)**: Quiet operation at 30% power
- **Night Mode (15%)**: Ultra-quiet operation at 15% power
- **Standby Mode**: Complete shutdown for silent nights

### 🤖 Smart Automation
- **10-minute Intervals**: Automatic solar power adjustments
- **Auto Standby**: Automatic shutdown when solar power drops below threshold
- **Auto Restart**: Automatic restart when solar power exceeds set point
- **Temperature Protection**: Auto-underclock at 75°C (configurable per miner)

## Supported Hardware

- **Antminer S19j Pro**
- **Antminer S19j Pro+**
- **Antminer S21+**
- **LuxOS Firmware** (required)

## Installation

### HACS Installation (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the "+" button
4. Search for "SolMiner"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/solminer` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click "Add Integration" and search for "SolMiner"

## Configuration

1. Go to **Configuration** > **Integrations**
2. Click **Add Integration**
3. Search for **SolMiner**
4. Enter your miner details:
   - **Host**: IP address of your miner (e.g., 192.168.1.210)
   - **Username**: Usually "root" (default)
   - **Password**: Usually "root" (default)
5. Click **Submit**

## Entity Types

### Sensors
- Hashrate metrics (5s, 1m, 15m averages)
- Power consumption and efficiency
- Temperature sensors (average, maximum, per-board)
- Fan speeds
- Solar power utilization
- Chip frequency and voltage
- Miner status and uptime

### Switches
- Mining enabled/disabled
- Individual hashboard control (Board 0, 1, 2)
- Solar curve mode toggle
- Auto power management
- Temperature protection

### Number Inputs
- Solar power input (manual)
- Maximum solar power (for curve simulation)
- Power limit settings
- Performance scaling (50-130%)
- Temperature threshold
- Fan speed override
- Chip frequency adjustment

### Select Dropdowns
- Power profiles (Max Power, Balanced, Ultra Eco, Manual)
- Quick power modes (Solar Max, Eco Mode, Night modes, Standby)
- Frequency profiles (-16 to +4)
- Operating modes (Normal, Solar Optimized, Night Quiet, etc.)
- Active mining pool selection

## Services

### `solminer.emergency_stop`
Immediately stops all mining operations and sets minimum power.

### `solminer.reboot_miner`
Reboots the selected miner device.

### `solminer.set_solar_mode`
Configures the miner for optimal solar power utilization.
- `max_power`: Maximum power to use when solar is available (W)

### `solminer.set_night_mode`
Configures the miner for quiet night operation.
- `power_percentage`: Percentage of normal power (0-50%)

### `solminer.apply_power_profile`
Applies a specific power profile.
- `profile`: Profile to apply (-16 to +4)

### `solminer.control_hashboard`
Controls individual hashboards.
- `board_id`: Board to control (0, 1, or 2)
- `enabled`: Enable or disable the board

## Solar Curve Simulation

The integration includes a 24-hour solar curve simulation that automatically adjusts mining power based on typical solar generation patterns:

- **Night (00:00-05:00, 18:00-23:00)**: 0-5% power
- **Morning (06:00-11:00)**: 5-85% power (gradual increase)
- **Peak (12:00-13:00)**: 95-100% power
- **Afternoon (14:00-17:00)**: 85-30% power (gradual decrease)

## Automation Examples

### Basic Solar Automation
```yaml
automation:
  - alias: "Solar Mining Control"
    trigger:
      - platform: numeric_state
        entity_id: number.solminer_solar_power_input
        above: 2000
    action:
      - service: solminer.set_solar_mode
        data:
          max_power: 4200
```

### Temperature Protection
```yaml
automation:
  - alias: "Miner Temperature Protection"
    trigger:
      - platform: numeric_state
        entity_id: sensor.solminer_temp_max
        above: 80
    action:
      - service: solminer.apply_power_profile
        data:
          profile: "-4"
```

### Night Mode Scheduler
```yaml
automation:
  - alias: "Night Mode Enable"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: solminer.set_night_mode
        data:
          power_percentage: 15
```

## Troubleshooting

### Connection Issues
- Verify the miner IP address is correct
- Ensure the miner is accessible on your network
- Check that LuxOS firmware is installed and running
- Try default credentials (root/root) if authentication fails

### API Errors
- Ensure the miner is not overloaded with requests
- Check Home Assistant logs for detailed error messages
- Verify the miner firmware supports the required API commands

### Performance Issues
- Adjust the update interval in integration options
- Reduce the number of enabled sensors if needed
- Check network latency to the miner

## Development

### Running Tests
```bash
cd SolMiner
pytest __tests__/ -v
```

### Project Structure
```
custom_components/solminer/
├── __init__.py          # Integration setup and services
├── config_flow.py       # Configuration flow
├── const.py            # Constants and defaults
├── coordinator.py      # Data coordinator
├── luxos_api.py        # LuxOS API client
├── manifest.json       # Integration manifest
├── sensor.py           # Sensor platform
├── switch.py           # Switch platform
├── number.py           # Number platform
├── select.py           # Select platform
├── services.yaml       # Service definitions
└── translations/       # Localization files
```

## Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests to the main repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- 📋 [Report Issues](https://github.com/user/solminer/issues)
- 💬 [Discussions](https://github.com/user/solminer/discussions)
- 📖 [Documentation](https://github.com/user/solminer/wiki)