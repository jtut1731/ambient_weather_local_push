"""The Ambient Weather Local Push integration."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_NAME,
    CONF_WEBHOOK_ID,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.storage import Store

from .const import (
    ATTR_KNOWN_SENSORS,
    ATTR_LAST_DATA,
    ATTR_LIGHTNING_DATA,
    ATTR_MAC,
    ATTR_SENSOR_UPDATE_IN_PROGRESS,
    ATTR_STATIONTYPE,
    CONF_NAME,
    DOMAIN,
    IGNORED_WEBHOOK_KEYS,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .const_binary_sensor import SUPPORTED_BINARY_SENSOR_TYPES
from .const_sensor import CALCULATED_SENSOR_TYPES, SUPPORTED_SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.WEATHER,
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up Ambient Weather Local Push from a config entry."""
    ambient = entry.runtime_data = AmbientStation(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ambient

    await ambient.async_load()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle Ambient Weather station webhook updates."""
        return await ambient.async_handle_webhook(request)

    webhook.async_register(
        hass,
        DOMAIN,
        entry.title,
        entry.data[CONF_WEBHOOK_ID],
        handle_webhook,
        local_only=True,
        allowed_methods=("GET", "POST"),
    )

    @callback
    def _unregister_webhook(_: Event) -> None:
        webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _unregister_webhook)
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload an Ambient Weather Local Push config entry."""
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_save()
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


class AmbientStation:
    """Handle Ambient Weather local push updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the station."""
        self._entry = entry
        self._hass = hass
        self.station: dict[str, Any] = {
            ATTR_MAC: entry.entry_id,
            ATTR_NAME: entry.data.get(CONF_NAME, entry.title),
            ATTR_LAST_DATA: {},
            ATTR_KNOWN_SENSORS: [],
            ATTR_LIGHTNING_DATA: {},
            ATTR_SENSOR_UPDATE_IN_PROGRESS: False,
            ATTR_STATIONTYPE: "",
        }
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
        self._update_event_handle = f"{DOMAIN}_data_update_{entry.entry_id}"

    @property
    def update_event_handle(self) -> str:
        """Return the dispatcher update signal for this station."""
        return self._update_event_handle

    async def async_load(self) -> None:
        """Load station metadata from storage."""
        if (data := await self._store.async_load()) is None:
            return

        self.station[ATTR_KNOWN_SENSORS] = data.get(ATTR_KNOWN_SENSORS, [])
        self.station[ATTR_LIGHTNING_DATA] = data.get(ATTR_LIGHTNING_DATA, {})

    async def async_save(self) -> None:
        """Save station metadata to storage."""
        await self._store.async_save(
            {
                ATTR_KNOWN_SENSORS: self.station[ATTR_KNOWN_SENSORS],
                ATTR_LIGHTNING_DATA: self.station[ATTR_LIGHTNING_DATA],
            }
        )

    async def async_handle_webhook(self, request: web.Request) -> web.Response:
        """Process a webhook request from the station."""
        if request.method == "GET":
            data = dict(request.query)
        elif request.method == "POST":
            data = dict(await request.post())
        else:
            raise web.HTTPMethodNotAllowed(request.method, ["GET", "POST"])

        await self.async_on_data(data)
        return web.Response(text="OK")

    async def async_on_data(self, data: dict[str, Any]) -> None:
        """Process incoming station data and notify entities."""
        self.station[ATTR_STATIONTYPE] = data.get(ATTR_STATIONTYPE, "")
        if passkey := data.get("PASSKEY"):
            self.station[ATTR_MAC] = str(passkey)

        extracted_data = {
            key: _coerce_value(key, value)
            for key, value in data.items()
            if key not in IGNORED_WEBHOOK_KEYS
            and key in (SUPPORTED_SENSOR_TYPES + SUPPORTED_BINARY_SENSOR_TYPES)
        }
        if not extracted_data:
            _LOGGER.debug(
                "Ambient webhook update had no supported sensor values: %s", data
            )
            return

        if (
            extracted_data == self.station[ATTR_LAST_DATA]
            and not self.station[ATTR_SENSOR_UPDATE_IN_PROGRESS]
        ):
            return

        self.station[ATTR_LAST_DATA] = extracted_data
        known_calc_sensors = [
            key
            for key, dependencies in CALCULATED_SENSOR_TYPES.items()
            if all(dependency in extracted_data for dependency in dependencies)
        ]
        known_sensors_set = set(
            self.station[ATTR_KNOWN_SENSORS]
            + known_calc_sensors
            + list(extracted_data)
        )
        new_sensors = known_sensors_set.difference(self.station[ATTR_KNOWN_SENSORS])

        if new_sensors:
            self.station[ATTR_KNOWN_SENSORS] = sorted(known_sensors_set)
            await self.async_save()
            await self._hass.config_entries.async_unload_platforms(
                self._entry, PLATFORMS
            )
            await self._hass.config_entries.async_forward_entry_setups(
                self._entry, PLATFORMS
            )
        else:
            await self.async_save()

        async_dispatcher_send(self._hass, self.update_event_handle)


class AmbientWeatherEntity(RestoreEntity):
    """Base entity for Ambient Weather Local Push."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, ambient: AmbientStation, description: EntityDescription
    ) -> None:
        """Initialize the entity."""
        self._ambient = ambient
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{ambient._entry.entry_id}_{description.key}"
        self._attr_available = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, ambient._entry.entry_id)},
            manufacturer="Ambient Weather",
            model="Weather Station",
            sw_version=ambient.station[ATTR_STATIONTYPE] or None,
            name=ambient.station[ATTR_NAME],
        )

    async def async_added_to_hass(self) -> None:
        """Register update callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self._ambient.update_event_handle,
                self.update,
            )
        )

    @callback
    def update_from_latest_data(self) -> None:
        """Update entity state from latest data."""
        raise NotImplementedError

    @callback
    def update(self) -> None:
        """Update the state."""
        last_data = self._ambient.station[ATTR_LAST_DATA]
        self._attr_available = last_data.get(self.entity_description.key) is not None
        self.update_from_latest_data()
        self.async_write_ha_state()


def _coerce_value(key: str, value: Any) -> Any:
    """Convert query-string values to native types where possible."""
    if key == "dateutc":
        return value
    if not isinstance(value, str):
        return value

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
