"""The Companion Bluetooth Proxy integration."""
from __future__ import annotations

import logging
from typing import Any

from aiohttp.web import Request, Response, json_response
import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .constants import CONF_WEBHOOK, DOMAIN, PLATFORMS
from .scanner import CompanionBLEScanner

_LOGGER = logging.getLogger(__name__)

# Legacy YAML configuration schema (not used with config flow)
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema({}, extra=vol.ALLOW_EXTRA),
    },
    extra=vol.ALLOW_EXTRA,
)


async def _async_handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: Request
) -> Response:
    """Handle incoming webhook data from companion app."""
    # Parse incoming JSON data
    try:
        message = await request.json()
    except ValueError:
        _LOGGER.warning("Invalid JSON received in webhook: %s", webhook_id)
        return json_response([])
    
    _LOGGER.debug("Webhook %s received data: %s", webhook_id, message)
    
    # Look up the scanner associated with this webhook
    webhooks = hass.data[DOMAIN]["webhooks"]
    scanners = hass.data[DOMAIN]["scanners"]
    
    if entry_id := webhooks.get(webhook_id):
        if scanner := scanners.get(entry_id):
            # Process each BLE advertisement in the message
            for item in message:
                await scanner.async_process_json(item)
            
            # Update sensor entities with new data
            await scanner.async_update_sensors()
        else:
            _LOGGER.warning("Scanner not found for webhook: %s", webhook_id)
    else:
        _LOGGER.warning("No entry registered for webhook: %s", webhook_id)
    
    return json_response([])


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Companion Bluetooth Proxy component.

    This is called once during Home Assistant startup and initializes
    the integration's data storage structure.

    """
    # Initialize storage for scanners and webhook mappings
    hass.data[DOMAIN] = {
        "scanners": {},  # Maps entry_id -> CompanionBLEScanner
        "webhooks": {},  # Maps webhook_id -> entry_id
    }
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Companion Bluetooth Proxy from a config entry.

    This is called when a user adds a new proxy device through the UI.

    """
    # Extract webhook ID from config entry
    hook_id = entry.data[CONF_WEBHOOK]
    
    # Create and initialize the BLE scanner
    scanner = CompanionBLEScanner(hass, entry)
    await scanner.async_load(hass)
    
    # Store scanner in both entry runtime_data and hass.data
    entry.runtime_data = scanner
    hass.data[DOMAIN]["scanners"][entry.entry_id] = scanner
    hass.data[DOMAIN]["webhooks"][hook_id] = entry.entry_id
    
    # Register webhook endpoint for receiving BLE data
    webhook.async_register(
        hass,
        DOMAIN,
        "Companion BT Proxy",
        hook_id,
        _async_handle_webhook,
    )
    
    _LOGGER.debug("Config entry setup complete. Webhook ID: %s", hook_id)
    
    # Set up platform entities (sensors)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    This is called when a user removes the integration or it's being reloaded.

    """
    # Get webhook ID and scanner
    hook_id = entry.data[CONF_WEBHOOK]
    scanner = entry.runtime_data
    
    # Unregister webhook
    webhook.async_unregister(hass, hook_id)
    
    # Unload platform entities
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Clean up scanner
        await scanner.async_unload(hass)
        
        # Remove from data storage
        hass.data[DOMAIN]["webhooks"].pop(hook_id, None)
        hass.data[DOMAIN]["scanners"].pop(entry.entry_id, None)
        entry.runtime_data = None
    
    return unload_ok
