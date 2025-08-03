"""Config flow for SolMiner integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, DEFAULT_USERNAME, DEFAULT_PASSWORD
from .luxos_api import LuxOSAPI, LuxOSAPIError

_LOGGER = logging.getLogger(__name__)

def validate_ip_or_hostname(value):
    """Validate IP address or hostname."""
    import re
    # Basic IP validation
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    
    if re.match(ip_pattern, value):
        # Validate IP ranges
        parts = value.split('.')
        if all(0 <= int(part) <= 255 for part in parts):
            return value
    elif re.match(hostname_pattern, value):
        return value
    
    raise vol.Invalid("Invalid IP address or hostname")

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): validate_ip_or_hostname,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): cv.string,
    }
)


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    api = LuxOSAPI(
        host=data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
    )
    
    try:
        # Test basic connectivity first
        _LOGGER.debug(f"Testing connection to {data[CONF_HOST]}")
        
        if not await api.test_connection():
            raise CannotConnect(f"Cannot reach miner at {data[CONF_HOST]}. Check IP address and network connectivity.")
        
        # Try to get basic miner info without authentication first
        try:
            summary = await api.get_summary()
            if summary:
                _LOGGER.debug("Connected successfully without authentication")
                return {"title": f"SolMiner {data[CONF_HOST]}"}
        except LuxOSAPIError:
            _LOGGER.debug("Basic connection failed, trying with authentication")
        
        # Try authentication methods
        login_success = await api.logon()
        if not login_success:
            # Try with different common credentials
            common_creds = [
                ("root", "root"),
                ("admin", "admin"),
                ("", "root"),
                ("root", ""),
                ("admin", ""),
                ("", "admin"),
            ]
            
            for username, password in common_creds:
                if username != data[CONF_USERNAME] or password != data[CONF_PASSWORD]:
                    test_api = LuxOSAPI(data[CONF_HOST], username, password)
                    try:
                        if await test_api.logon():
                            _LOGGER.info(f"Authentication successful with {username}:{password}")
                            await test_api.logoff()
                            await test_api.close()
                            # Update the working credentials
                            data[CONF_USERNAME] = username
                            data[CONF_PASSWORD] = password
                            return {"title": f"SolMiner {data[CONF_HOST]}"}
                    except LuxOSAPIError:
                        pass
                    finally:
                        await test_api.close()
            
            raise InvalidAuth("Unable to authenticate with provided or common credentials")
        
        # Test that we can get miner data
        try:
            summary = await api.get_summary()
            if not summary:
                raise CannotConnect("Connected but unable to retrieve miner data")
        except LuxOSAPIError as err:
            _LOGGER.warning(f"Authentication succeeded but data retrieval failed: {err}")
            # Don't fail here - some commands might work even if summary doesn't
        
        await api.logoff()
        return {"title": f"SolMiner {data[CONF_HOST]}"}
    
    except LuxOSAPIError as err:
        _LOGGER.error(f"Connection/authentication failed: {err}")
        if any(x in str(err).lower() for x in ["connection", "timeout", "unreachable", "refused", "404", "500"]):
            raise CannotConnect from err
        else:
            raise InvalidAuth from err
    except Exception as err:
        _LOGGER.error(f"Unexpected error during validation: {err}")
        if any(x in str(err).lower() for x in ["connection", "timeout", "unreachable", "refused"]):
            raise CannotConnect from err
        else:
            raise InvalidAuth from err
    finally:
        await api.close()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SolMiner."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""