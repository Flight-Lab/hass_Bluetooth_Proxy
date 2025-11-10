"""Constants for the Companion Bluetooth Proxy integration."""
from __future__ import annotations

DOMAIN = "companion_bt_proxy"
PLATFORMS = ("sensor",)  # Using tuple since this is immutable

# Configuration keys
CONF_WEBHOOK = "webhook"

# Attribute keys
ATTR_WEBHOOK_ID = "webhook_id"