"""LuxOS API client for Antminer devices."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)


class LuxOSAPIError(Exception):
    """Exception for LuxOS API errors."""


class LuxOSAPI:
    """LuxOS API client for Antminer devices."""

    def __init__(self, host: str, username: str = "root", password: str = "root") -> None:
        """Initialize the LuxOS API client."""
        self.host = host
        self.username = username
        self.password = password
        self.session_id: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session_id:
            await self.logoff()
        if self._session and not self._session.closed:
            await self._session.close()

    async def _send_command(self, command: str, parameter: str = "") -> Dict[str, Any]:
        """Send a command to the LuxOS API."""
        session = await self._get_session()
        
        # Try different API endpoints and formats
        endpoints = [
            "/cgi-bin/luci/api",
            "/cgi-bin/api.cgi", 
            "/api",
            "/cgi-bin/minerapi.cgi"
        ]
        
        for endpoint in endpoints:
            try:
                # Format 1: JSON payload
                payload = {
                    "command": command,
                    "parameter": parameter
                }
                
                if self.session_id:
                    payload["session_id"] = self.session_id

                async with session.post(
                    f"http://{self.host}{endpoint}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "error" not in result:
                            return result
                        elif endpoint == endpoints[-1]:  # Last endpoint, raise error
                            raise LuxOSAPIError(f"API Error: {result['error']}")
                    elif response.status == 404 and endpoint != endpoints[-1]:
                        continue  # Try next endpoint
                    else:
                        error_text = await response.text()
                        if endpoint == endpoints[-1]:  # Last endpoint, raise error
                            raise LuxOSAPIError(f"HTTP {response.status}: {error_text}")
                
            except aiohttp.ClientError:
                if endpoint == endpoints[-1]:  # Last endpoint, raise error
                    raise
                continue  # Try next endpoint
            except json.JSONDecodeError:
                if endpoint == endpoints[-1]:  # Last endpoint, raise error
                    raise
                continue  # Try next endpoint
        
        # If we get here, try CGMiner-style API
        return await self._send_cgminer_command(command, parameter)
    
    async def _send_cgminer_command(self, command: str, parameter: str = "") -> Dict[str, Any]:
        """Send a CGMiner-style API command."""
        session = await self._get_session()
        
        # CGMiner API typically uses port 4028 with socket-like protocol
        # For HTTP, try different formats
        try:
            # Format: command+parameters
            cmd_string = command
            if parameter:
                cmd_string += f"+{parameter}"
            
            async with session.get(
                f"http://{self.host}:4028/{cmd_string}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    # Try to parse as JSON
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        # Return as plain text wrapped in dict
                        return {"result": text}
        except aiohttp.ClientError:
            pass
        
        # Final attempt: Basic HTTP endpoint
        try:
            async with session.get(
                f"http://{self.host}/cgi-bin/minerApi.cgi",
                params={"command": command, "parameter": parameter}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    raise LuxOSAPIError(f"HTTP {response.status}: {await response.text()}")
        except aiohttp.ClientError as err:
            raise LuxOSAPIError(f"Connection error: {err}")
        except json.JSONDecodeError as err:
            raise LuxOSAPIError(f"Invalid JSON response: {err}")

    async def logon(self) -> bool:
        """Authenticate and create a session."""
        # Try different authentication formats
        auth_formats = [
            f"{self.username},{self.password}",  # Common LuxOS format
            f"{self.username}:{self.password}",  # Colon separator
            f"{self.username}|{self.password}",  # Pipe separator
            self.password,  # Password only
            f"{self.username}",  # Username only
        ]
        
        for auth_format in auth_formats:
            try:
                _LOGGER.debug(f"Trying authentication format: {auth_format[:5]}...")
                result = await self._send_command("logon", auth_format)
                
                if isinstance(result, dict):
                    if "session_id" in result:
                        self.session_id = result["session_id"]
                        _LOGGER.debug("Successfully authenticated with LuxOS API")
                        return True
                    elif "STATUS" in result and len(result["STATUS"]) > 0:
                        status = result["STATUS"][0]
                        if status.get("STATUS") == "S":  # Success
                            _LOGGER.debug("Authentication successful (no session required)")
                            return True
                
            except LuxOSAPIError as e:
                _LOGGER.debug(f"Auth format failed: {e}")
                continue
        
        # Try without authentication (some miners don't require it)
        try:
            _LOGGER.debug("Trying without authentication")
            result = await self._send_command("summary")
            if result:
                _LOGGER.debug("No authentication required")
                return True
        except LuxOSAPIError:
            pass
        
        _LOGGER.error("Failed to authenticate with LuxOS API - all methods exhausted")
        return False

    async def logoff(self) -> None:
        """End the current session."""
        if self.session_id:
            try:
                await self._send_command("logoff")
                self.session_id = None
            except LuxOSAPIError:
                _LOGGER.warning("Failed to properly log off from LuxOS API")

    async def get_summary(self) -> Dict[str, Any]:
        """Get miner summary information."""
        return await self._send_command("summary")

    async def get_stats(self) -> Dict[str, Any]:
        """Get detailed miner statistics."""
        return await self._send_command("stats")

    async def get_pools(self) -> Dict[str, Any]:
        """Get mining pool information."""
        return await self._send_command("pools")

    async def get_version(self) -> Dict[str, Any]:
        """Get version information."""
        return await self._send_command("version")

    async def get_devs(self) -> Dict[str, Any]:
        """Get device information."""
        return await self._send_command("devs")

    async def pause_mining(self) -> Dict[str, Any]:
        """Pause all mining operations."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("pause")

    async def resume_mining(self) -> Dict[str, Any]:
        """Resume mining operations."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("resume")

    async def reboot_device(self) -> Dict[str, Any]:
        """Reboot the miner."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("reboot")

    async def enable_board(self, board_id: int) -> Dict[str, Any]:
        """Enable a specific hashboard."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("enableboard", str(board_id))

    async def disable_board(self, board_id: int) -> Dict[str, Any]:
        """Disable a specific hashboard."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("disableboard", str(board_id))

    async def set_frequency(self, frequency: int) -> Dict[str, Any]:
        """Set chip frequency."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("frequencyset", str(frequency))

    async def get_frequency(self) -> Dict[str, Any]:
        """Get current chip frequency."""
        return await self._send_command("frequencyget")

    async def set_profile(self, profile: str) -> Dict[str, Any]:
        """Set power profile."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("profileset", profile)

    async def get_profile(self) -> Dict[str, Any]:
        """Get current power profile."""
        return await self._send_command("profileget")

    async def set_power_limit(self, watts: int) -> Dict[str, Any]:
        """Set power limit in watts."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("power", str(watts))

    async def curtail_power(self, percentage: float) -> Dict[str, Any]:
        """Curtail power by percentage."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("curtail", str(percentage))

    async def get_health_chip(self) -> Dict[str, Any]:
        """Get chip health information."""
        return await self._send_command("healthchipget")

    async def set_fan_speed(self, speed: int) -> Dict[str, Any]:
        """Set fan speed."""
        if not self.session_id:
            await self.logon()
        return await self._send_command("fanset", str(speed))