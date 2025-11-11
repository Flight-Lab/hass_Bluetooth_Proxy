"""Sensor platform for Companion Bluetooth Proxy integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import sensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .constants import DOMAIN
from .scanner import CompanionBLEScanner

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    scanner: CompanionBLEScanner = entry.runtime_data
    async_add_entities([_LastUpdate(scanner, entry)])


class _LastUpdate(sensor.SensorEntity):
    """Sensor that tracks the last time BLE data was received."""

    def __init__(self, scanner: CompanionBLEScanner, entry: ConfigEntry) -> None:
        """Initialize the Last Update sensor."""
        self._attr_has_entity_name = True
        self._attr_unique_id = f"bt_proxy_{entry.entry_id}_last_update"
        self._attr_name = "Last Update"

        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_class = sensor.SensorDeviceClass.TIMESTAMP

        # Register this sensor with the scanner for update notifications
        scanner._sensors.append(self)

        # Store sensor state
        self._value: dt_util.dt.datetime | None = None

        # Device information
        self._entry_id = entry.entry_id
        self._device_name = entry.title

    async def async_on_scanner_update(self, scanner: CompanionBLEScanner) -> None:
        """Handle scanner update notification."""
        self._value = dt_util.now()
        self.async_write_ha_state()

    @property
    def native_value(self) -> dt_util.dt.datetime | None:
        """Return the timestamp of last update."""
        return self._value

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information for grouping entities."""
        return {
            "identifiers": {
                ("entry_id", self._entry_id),
            },
            "name": self._device_name,
        }