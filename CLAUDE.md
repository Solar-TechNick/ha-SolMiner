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

The component integrates with two main APIs:

### LuxOS Firmware API
- Base URL: `https://docs.luxor.tech/`
- Key commands: `enableboard`, `disableboard`, `frequencyset`, `profileset`, `power`, `curtail`
- Used for direct miner control (power profiles, hashboard management, temperature control)

### pyASIC Library Integration
- Reference implementation: `https://docs.pyasic.org`
- Provides async standardized interface for ASIC miner control
- Uses `MinerData` and `MinerConfig` dataclasses for consistent data representation

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

## Testing Requirements

- Place tests in `__tests__` directory
- Test all major functionality including edge cases and error scenarios
- Verify computed values update correctly
- Aim for high code coverage

## Reference Implementation

The component should follow patterns similar to `https://github.com/Schnitzel/hass-miner` for Home Assistant integration best practices.