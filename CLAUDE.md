# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SolMiner is a Home Assistant custom component/integration for solar-powered Bitcoin mining operations. The project controls Antminer devices (S19j Pro, S19j Pro+, S21+) running LuxOS firmware, optimizing mining operations based on available solar power.

## Hardware Configuration

Three Antminer devices are configured:
- Antminer S19j Pro+: http://192.168.1.210
- Antminer S19j Pro: http://192.168.1.211  
- Antminer S21+: http://192.168.1.212

## API Integration

The component uses a dual-API approach for maximum compatibility:

### Primary: CGMiner API (Port 4028)
- **Protocol**: TCP socket communication on port 4028
- **Format**: JSON command/response over TCP
- **Authentication**: None required
- **Compatibility**: Excellent for S21+ and LuxOS firmware
- **Commands**: `summary`, `stats`, `devs`, `pools`, `version`, `ascenable`, `ascdisable`
- **Verified working** with S21+ running LuxOS 2025.7.10.152155

### Fallback: LuxOS HTTP API
- **Protocol**: HTTP POST to various endpoints
- **Endpoints**: `/cgi-bin/luci/api`, `/cgi-bin/api.cgi`, `/api`
- **Authentication**: Session-based with `logon`/`logoff`
- **Commands**: `enableboard`, `disableboard`, `frequencyset`, `profileset`, `power`, `curtail`
- **Used when**: CGMiner API unavailable or for specific LuxOS features

### API Client Features
- **Auto-detection**: Tries CGMiner API first, falls back to HTTP
- **Multiple auth methods**: Supports various credential formats (comma, colon, pipe separators)
- **Error handling**: Comprehensive timeout and connection error handling
- **Logging**: Debug logging for troubleshooting API issues

## Core Features Architecture

### Power Management System
- **Solar Integration**: Manual power input (0-50000W) and sun curve automation
- **Power Profiles**: Max Power (+2), Balanced (default), Ultra Eco (-2), Manual (-16 to +4)
- **Performance Scaling**: 50% to 130% adjustment range
- **Automatic Curtailment**: 10-minute interval solar power adjustments

### Hashboard Control
- Individual control of boards 0, 1, and 2
- Real-time monitoring of temperature, frequency, voltage per board
- Smart automation based on solar power availability

### Operational Modes
- **Mining Control**: Pause/Resume, Solar Max (4200W), Eco Mode (1500W), Emergency Stop
- **Night Operations**: 30%/15% power modes, complete standby
- **Temperature Protection**: Auto-underclock at 75°C (configurable per miner)

## Implementation Details

### File Structure
```
custom_components/solminer/
├── __init__.py           # Integration setup and services
├── config_flow.py        # UI-based configuration
├── const.py             # Constants and default values
├── coordinator.py       # Data coordinator with solar management
├── luxos_api.py         # Dual API client (CGMiner + HTTP)
├── manifest.json        # Integration manifest
├── sensor.py            # Sensor entities (hashrate, temp, power)
├── switch.py            # Switch entities (mining, boards, automation)
├── number.py            # Number entities (power limits, scaling)
├── select.py            # Select entities (profiles, modes)
├── services.yaml        # Service definitions
└── translations/        # Localization files
```

### Key Classes
- **LuxOSAPI**: Dual-protocol API client with auto-detection
- **SolMinerCoordinator**: Data coordinator with solar curve simulation
- **Config Flow**: Robust connection testing with multiple credential attempts

### Troubleshooting
- **Connection Issues**: Check IP addresses and network connectivity first
- **500 Server Errors**: Usually config flow validation issues - check Home Assistant logs
- **Authentication Failures**: Try common credentials (root/root, admin/admin, empty)
- **S21+ Compatibility**: Uses CGMiner API (port 4028) - verify port is open

### Testing Requirements
- Place tests in `__tests__` directory
- Test scripts available: `test_s21_api.py`, `simple_s21_test.py`
- Test all major functionality including edge cases and error scenarios
- Verify computed values update correctly
- S21+ connectivity verified at 192.168.1.212

### Development Commands
```bash
# Test S21+ connectivity
python3 simple_s21_test.py

# Run integration tests  
pytest __tests__/ -v

# Check Home Assistant logs for debugging
tail -f /config/home-assistant.log | grep solminer
```

## Reference Implementation

The component follows patterns similar to `https://github.com/Schnitzel/hass-miner` for Home Assistant integration best practices, with enhanced CGMiner API support for better Antminer compatibility.