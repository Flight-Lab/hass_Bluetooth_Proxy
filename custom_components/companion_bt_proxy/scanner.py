"""Bluetooth scanner implementation for Companion Bluetooth Proxy."""
from __future__ import annotations

import base64
from collections.abc import Callable
import logging
import time
from typing import Any

from bluetooth_data_tools import monotonic_time_coarse

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class CompanionBLEScanner(bluetooth.BaseHaRemoteScanner):
    """Scanner that processes BLE advertisements from companion app."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the BLE scanner."""
        # Create connector that doesn't allow direct connections
        # (companion app handles connections, not Home Assistant)
        self._connector = bluetooth.HaBluetoothConnector(
            client=None, source=entry.entry_id, can_connect=lambda: False
        )
        super().__init__(entry.entry_id, entry.title, self._connector, False)
        self._sensors: list = []
        self._unload_callback: Callable[[], None] | None = None

    async def async_process_json(self, data: dict[str, Any]) -> None:
        """Process BLE advertisement data from companion app.

        Converts JSON format to Home Assistant's Bluetooth integration format.
        Handles base64 decoding and timestamp conversion from Unix to monotonic time.
        """
        # Decode base64-encoded service data
        service_data = {
            key: base64.b64decode(value)
            for key, value in data.get("service_data", {}).items()
        }

        # Decode base64-encoded manufacturer data (keys are integer company IDs)
        manufacturer_data = {
            int(key, 10): base64.b64decode(value)
            for key, value in data.get("manufacturer_data", {}).items()
        }

        _LOGGER.debug(
            "Processing BLE advertisement: address=%s, rssi=%s",
            data.get("address"),
            data.get("rssi"),
        )

        # Convert received timestamp to monotonic time for HA's Bluetooth system
        # The companion app sends Unix timestamps, but HA uses monotonic time
        current_monotonic = monotonic_time_coarse()
        received_timestamp_seconds = data.get("timestamp", 0) / 1000.0
        current_time_seconds = time.time()
        time_offset = current_time_seconds - received_timestamp_seconds
        advertisement_monotonic_time = current_monotonic - time_offset

        # Pass advertisement to HA's Bluetooth integration
        self._async_on_advertisement(
            address=data["address"],
            rssi=data.get("rssi", 0),
            local_name=data.get("name"),
            service_uuids=data.get("service_uuids", []),
            service_data=service_data,
            manufacturer_data=manufacturer_data,
            tx_power=data.get("tx_power", 0),
            details={},
            advertisement_monotonic_time=advertisement_monotonic_time,
        )

    async def async_update_sensors(self) -> None:
        """Notify all registered sensor entities of new data."""
        for sensor in self._sensors:
            await sensor.async_on_scanner_update(self)

    async def async_load(self, hass: HomeAssistant) -> None:
        """Register scanner with Home Assistant's Bluetooth system."""
        # Register with priority 0 (default) and store unload callback
        self._unload_callback = bluetooth.async_register_scanner(hass, self, 0)

    async def async_unload(self, hass: HomeAssistant) -> None:
        """Unregister scanner and clear references."""
        if self._unload_callback:
            self._unload_callback()
        self._sensors = []