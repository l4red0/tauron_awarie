"""Sensor platform for Tauron Awarie integration."""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp.resolver import ThreadedResolver
from homeassistant.components.sensor import SensorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ATTRIBUTION,
    ATTR_NEXT_END,
    ATTR_NEXT_MESSAGE,
    ATTR_NEXT_START,
    ATTR_NEXT_TYPE,
    ATTR_OUTAGE_COUNT,
    ATTR_OUTAGES,
    ATTRIBUTION,
    CONF_CALENDAR_ENTITY,
    CONF_CITY_AREA_ID,
    CONF_CITY_NAME,
    CONF_COMMUNE_GAID,
    CONF_COMMUNE_NAME,
    CONF_CREATE_CALENDAR,
    CONF_DISTRICT_GAID,
    CONF_DISTRICT_NAME,
    CONF_PROVINCE_GAID,
    DOMAIN,
    OUTAGE_TYPE,
)
from .outages import Outage, OutageParams, TauronOutageFetcher

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=12)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tauron Awarie sensor from a config entry."""
    # Create session with threaded resolver to avoid DNS issues
    # Each config entry gets its own session to avoid sharing issues
    connector = aiohttp.TCPConnector(
        resolver=ThreadedResolver(),
        limit=10,
        limit_per_host=2,
    )
    session = aiohttp.ClientSession(connector=connector)

    # Store session reference for cleanup
    config_entry.runtime_data = {"session": session}

    async_add_entities(
        [TauronAwarieSensor(session, config_entry)],
        update_before_add=True,
    )


class TauronAwarieSensor(SensorEntity):
    """Sensor showing days until next Tauron outage."""

    _attr_native_unit_of_measurement = "days"

    def __init__(
        self,
        session: object,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        self._session = session  # Store session for cleanup
        data = entry.data
        self._params = OutageParams(
            province_gaid=data[CONF_PROVINCE_GAID],
            district_gaid=data[CONF_DISTRICT_GAID],
            commune_gaid=data[CONF_COMMUNE_GAID],
            city_area_id=data.get(CONF_CITY_AREA_ID, 0),
        )

        city = data.get(CONF_CITY_NAME, "")
        commune = data.get(CONF_COMMUNE_NAME, "")
        district = data.get(CONF_DISTRICT_NAME, str(self._params.district_gaid))

        base_parts = [p for p in (commune, city) if p]
        base_name = " ".join(base_parts) if base_parts else district
        self._attr_name = f"Tauron Awarie {base_name}"

        uid_parts = [str(self._params.district_gaid)]
        if commune:
            uid_parts.append(commune)
        if city:
            uid_parts.append(city)
        if self._params.city_area_id:
            uid_parts.append(str(self._params.city_area_id))
        self._attr_unique_id = "tauron_awarie_" + "_".join(uid_parts).lower().replace(
            " ",
            "_",
        )

        self._district_name = district
        self._city_name = city
        self._fetcher = TauronOutageFetcher(session)
        self._attr_native_value: int | None = None
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._outages: list[Outage] = []

        self._create_calendar = data.get(CONF_CREATE_CALENDAR, False)
        self._calendar_entity: str = data.get(CONF_CALENDAR_ENTITY, "")
        self._posted_event_ids: set[str] = set()

    @property
    def icon(self) -> str:
        """Return icon based on whether an outage is upcoming."""
        if self._attr_native_value is not None and self._attr_native_value >= 0:
            return "mdi:power-plug-off"
        return "mdi:power-plug"

    @property
    def device_info(self) -> dict[str, Any]:
        """Group entities under a device."""
        identifier = f"{self._params.district_gaid}_{self._city_name}".lower().replace(
            " ",
            "_",
        )
        return {
            "identifiers": {(DOMAIN, identifier)},
            "name": f"Tauron Awarie - {self._district_name}",
            "manufacturer": "Tauron Dystrybucja",
            "model": "Awarie",
        }

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def async_update(self) -> None:
        """Fetch fresh outage data from the WAAPI."""
        try:
            _LOGGER.debug(
                "Fetching outages: province=%s district=%s commune=%s area=%s",
                self._params.province_gaid,
                self._params.district_gaid,
                self._params.commune_gaid,
                self._params.city_area_id,
            )
            outages = await self._fetcher.fetch_outages(self._params)
            self._outages = outages

            now = datetime.now(UTC)
            active = [o for o in outages if o.end_date > now]
            next_outage = min(active, key=lambda o: o.start_date) if active else None

            self._attr_native_value = None
            self._attr_extra_state_attributes = self._base_attrs(
                len(active),
                next_outage,
                active,
            )

            if next_outage:
                delta_s = max((next_outage.start_date - now).total_seconds(), 0)
                self._attr_native_value = math.ceil(delta_s / 86400.0)

            if self._create_calendar and self._calendar_entity:
                await self._sync_calendar(active)

        except Exception:
            _LOGGER.exception("Error during outage update")
            self._attr_native_value = None

    # ------------------------------------------------------------------
    # Attributes
    # ------------------------------------------------------------------

    def _base_attrs(
        self,
        count: int,
        next_outage: Outage | None,
        active: list[Outage],
    ) -> dict[str, Any]:
        """Build extra state attributes dict."""
        attrs: dict[str, Any] = {
            ATTR_NEXT_START: None,
            ATTR_NEXT_END: None,
            ATTR_NEXT_MESSAGE: "",
            ATTR_NEXT_TYPE: None,
            ATTR_OUTAGE_COUNT: count,
            ATTR_OUTAGES: [
                {
                    "id": o.outage_id,
                    "start": o.start_date.isoformat(),
                    "end": o.end_date.isoformat(),
                    "message": o.message,
                    "type": OUTAGE_TYPE.get(o.type_id, str(o.type_id)),
                }
                for o in active
            ],
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }
        if next_outage:
            attrs[ATTR_NEXT_START] = next_outage.start_date.isoformat()
            attrs[ATTR_NEXT_END] = next_outage.end_date.isoformat()
            attrs[ATTR_NEXT_MESSAGE] = next_outage.message
            attrs[ATTR_NEXT_TYPE] = OUTAGE_TYPE.get(
                next_outage.type_id,
                str(next_outage.type_id),
            )
        return attrs

    # ------------------------------------------------------------------
    # Calendar sync
    # ------------------------------------------------------------------

    async def _sync_calendar(self, outages: list[Outage]) -> None:
        """Create timed calendar events for outages (idempotent)."""
        if not self.hass:
            return
        for outage in outages:
            if outage.outage_id in self._posted_event_ids:
                continue

            outage_type = OUTAGE_TYPE.get(outage.type_id, "Awaria")
            summary = f"Tauron {outage_type}"
            if self._city_name:
                summary = f"{summary} - {self._city_name}"

            local_start = dt_util.as_local(outage.start_date)
            local_end = dt_util.as_local(outage.end_date)

            if await self._calendar_event_exists(summary, outage.message, local_start):
                self._posted_event_ids.add(outage.outage_id)
                continue

            try:
                await self.hass.services.async_call(
                    "calendar",
                    "create_event",
                    {
                        "entity_id": self._calendar_entity,
                        "summary": summary,
                        "description": outage.message,
                        "start_date_time": local_start.isoformat(),
                        "end_date_time": local_end.isoformat(),
                    },
                    blocking=True,
                )
                self._posted_event_ids.add(outage.outage_id)
                _LOGGER.debug("Created calendar event for outage %s", outage.outage_id)
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Failed to create calendar event for %s",
                    outage.outage_id,
                    exc_info=True,
                )

    async def async_will_remove_from_hass(self) -> None:
        """Entity is being removed from Home Assistant."""
        # Session cleanup is handled at the config entry level

    async def _calendar_event_exists(
        self,
        summary: str,
        description: str,
        start: datetime,
    ) -> bool:
        """Check whether a matching calendar event already exists."""
        try:
            comp = self.hass.data.get("calendar")
            if not comp:
                return False
            entity = comp.get_entity(self._calendar_entity)
            if not entity:
                return False
            day_start = dt_util.start_of_local_day(start)
            day_end = day_start + timedelta(days=1)
            events = await entity.async_get_events(self.hass, day_start, day_end)
            for ev in events:
                ev_summary = getattr(ev, "summary", "") or ""
                ev_desc = getattr(ev, "description", "") or ""
                if ev_summary == summary and ev_desc == description:
                    return True
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Calendar duplicate check failed", exc_info=True)
        return False
