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
                timeout=aiohttp.ClientTimeout(total=15, connect=5),
                connector=aiohttp.TCPConnector(limit=10, limit_per_host=10)
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session_id:
            await self.logoff()
        if self._session and not self._session.closed:
            await self._session.close()

    async def test_connection(self) -> bool:
        """Test basic connectivity to the miner."""
        session = await self._get_session()
        
        # Test basic HTTP connectivity
        try:
            async with session.get(
                f"http://{self.host}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status < 500  # Any response (even 404) means it's reachable
        except Exception as err:
            _LOGGER.debug(f"Connection test failed: {err}")
            return False

    async def _send_command(self, command: str, parameter: str = "") -> Dict[str, Any]:
        """Send a command to the miner API."""
        # For S21+ compatibility, try CGMiner API first (port 4028)
        try:
            _LOGGER.debug(f"Trying CGMiner API for command: {command}")
            return await self._send_cgminer_command(command, parameter)
        except LuxOSAPIError as e:
            _LOGGER.debug(f"CGMiner API failed: {e}, trying HTTP endpoints")
        
        # Fallback to HTTP-based LuxOS API endpoints
        session = await self._get_session()
        
        endpoints = [
            "/cgi-bin/luci/api",
            "/cgi-bin/api.cgi", 
            "/api",
            "/cgi-bin/minerapi.cgi"
        ]
        
        for endpoint in endpoints:
            try:
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
                            _LOGGER.debug(f"HTTP API success on {endpoint}")
                            return result
                        elif endpoint == endpoints[-1]:
                            raise LuxOSAPIError(f"API Error: {result['error']}")
                    elif response.status == 404 and endpoint != endpoints[-1]:
                        continue
                    else:
                        error_text = await response.text()
                        if endpoint == endpoints[-1]:
                            raise LuxOSAPIError(f"HTTP {response.status}: {error_text}")
                
            except aiohttp.ClientError:
                if endpoint == endpoints[-1]:
                    raise LuxOSAPIError("All HTTP endpoints failed")
                continue
            except json.JSONDecodeError:
                if endpoint == endpoints[-1]:
                    raise LuxOSAPIError("Invalid JSON from all HTTP endpoints")
                continue
        
        raise LuxOSAPIError("All API methods failed")
    
    async def _send_cgminer_command(self, command: str, parameter: str = "") -> Dict[str, Any]:
        """Send a CGMiner-style API command using TCP socket."""
        import socket
        import asyncio
        
        try:
            # CGMiner API uses TCP socket on port 4028
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, 4028),
                timeout=10.0
            )
            
            # Prepare command
            cmd_data = {"command": command}
            if parameter:
                cmd_data["parameter"] = parameter
                
            # Send command as JSON
            cmd_json = json.dumps(cmd_data).encode() + b'\n'
            writer.write(cmd_json)
            await writer.drain()
            
            # Read response
            response_data = await asyncio.wait_for(
                reader.read(8192),
                timeout=10.0
            )
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            if response_data:
                try:
                    result = json.loads(response_data.decode().strip())
                    _LOGGER.debug(f"CGMiner API response for {command}: {result}")
                    return result
                except json.JSONDecodeError as e:
                    # Some responses might not be valid JSON
                    _LOGGER.warning(f"Invalid JSON from CGMiner API: {response_data[:200]}")
                    return {"raw_response": response_data.decode()[:1000]}
            else:
                raise LuxOSAPIError("No response from CGMiner API")
                
        except asyncio.TimeoutError:
            raise LuxOSAPIError("Timeout connecting to CGMiner API")
        except ConnectionRefusedError:
            raise LuxOSAPIError("CGMiner API connection refused (port 4028)")
        except Exception as err:
            raise LuxOSAPIError(f"CGMiner API error: {err}")

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
        
        # Try without authentication (CGMiner API typically doesn't require auth)
        try:
            _LOGGER.debug("Trying without authentication (CGMiner API)")
            result = await self._send_command("summary")
            if result and "STATUS" in result:
                _LOGGER.debug("CGMiner API working without authentication")
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
        try:
            if not self.session_id:
                await self.logon()
            return await self._send_command("enableboard", str(board_id))
        except LuxOSAPIError:
            # CGMiner API alternative
            return await self._send_command("ascenable", str(board_id))

    async def disable_board(self, board_id: int) -> Dict[str, Any]:
        """Disable a specific hashboard."""
        try:
            if not self.session_id:
                await self.logon()
            return await self._send_command("disableboard", str(board_id))
        except LuxOSAPIError:
            # CGMiner API alternative
            return await self._send_command("ascdisable", str(board_id))

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
        # Try LuxOS command first
        try:
            if not self.session_id:
                await self.logon()
            return await self._send_command("profileset", profile)
        except LuxOSAPIError:
            # Fallback for CGMiner API - some miners use different commands
            try:
                return await self._send_command("luxset", f"profile,{profile}")
            except LuxOSAPIError:
                # Last resort - try frequency adjustment
                freq_map = {
                    "+4": "750", "+3": "725", "+2": "700", "+1": "675",
                    "0": "650", "-1": "625", "-2": "600", "-3": "575", "-4": "550"
                }
                if profile in freq_map:
                    return await self._send_command("ascset", f"0,freq,{freq_map[profile]}")
                raise

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