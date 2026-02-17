"""Config flow for Tauron Awarie integration."""

from __future__ import annotations

import csv
import json
import logging
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import section

from .const import (
    CONF_CALENDAR_ENTITY,
    CONF_CITY_AREA_ID,
    CONF_CITY_GAID,
    CONF_CITY_NAME,
    CONF_COMMUNE_GAID,
    CONF_COMMUNE_NAME,
    CONF_CREATE_CALENDAR,
    CONF_DISTRICT_GAID,
    CONF_DISTRICT_NAME,
    CONF_PROVINCE_GAID,
    CONF_PROVINCE_NAME,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_CSV_PATH = _DATA_DIR / "tauron_cities.csv"
_AREAS_PATH = _DATA_DIR / "tauron_cities_areas.yml"
_MAX_RESULTS = 50
_MIN_QUERY_LENGTH = 3
_BACK_OPTION = "_back"


# ------------------------------------------------------------------
# Helpers (blocking I/O - run via async_add_executor_job)
# ------------------------------------------------------------------


def _load_city_areas() -> dict[int, list[dict[str, Any]]]:
    """Load city areas from JSON file keyed by GAID (= CSV DistrictGAID)."""
    try:
        with _AREAS_PATH.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return {
            entry["GAID"]: entry["CityAreas"]
            for entry in data
            if "GAID" in entry and "CityAreas" in entry
        }
    except Exception:
        _LOGGER.exception("Failed to load city areas file")
        return {}


def _search_cities(query: str) -> list[dict[str, Any]]:
    """Search CSV for cities matching *query* (deduped by GAID)."""
    query_lower = query.lower()
    results: dict[int, dict[str, Any]] = {}
    try:
        with _CSV_PATH.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = row.get("Name", "")
                if name.lower().startswith(query_lower):
                    gaid = int(row["GAID"])
                    if gaid not in results:
                        results[gaid] = {
                            "gaid": gaid,
                            "name": name,
                            "province_gaid": int(row["ProvinceGAID"]),
                            "district_gaid": int(row["DistrictGAID"]),
                            "commune_gaid": int(row["OwnerGAID"]),
                            "commune_name": row["CommuneName"],
                            "district_name": row["DistrictName"],
                            "province_name": row["ProvinceName"],
                        }
    except Exception:
        _LOGGER.exception("Failed to search cities CSV")

    def _sort_key(item: dict[str, Any]) -> tuple[int, str]:
        n = item["name"].lower()
        return (0, n) if n == query_lower else (1, n)

    return sorted(results.values(), key=_sort_key)


# ------------------------------------------------------------------
# Config flow
# ------------------------------------------------------------------


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tauron Awarie."""

    VERSION = 2
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize."""
        self._search_results: list[dict[str, Any]] = []
        self._selected_city: dict[str, Any] = {}
        self._city_areas_map: dict[int, list[dict[str, Any]]] = {}
        self._create_calendar: bool = True
        self._calendar_entity: str = ""

    # ---------- step 1: city search + calendar + optional manual ----------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """City name search, calendar toggle, or manual GAID entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store calendar settings for later entry creation
            self._create_calendar = user_input.get(CONF_CREATE_CALENDAR, True)
            self._calendar_entity = user_input.get(CONF_CALENDAR_ENTITY, "") or ""

            # Manual GAID path - check if GAID fields are filled
            manual = user_input.get("manual") or {}
            p = manual.get(CONF_PROVINCE_GAID, 0)
            d = manual.get(CONF_DISTRICT_GAID, 0)
            c = manual.get(CONF_COMMUNE_GAID, 0)
            a = manual.get(CONF_CITY_AREA_ID, 0)

            if p and d and c:
                # Manual GAIDs are provided, use them
                return await self._async_create_manual_entry(p, d, c, a)
            elif p or d or c or a:
                # Some fields filled but not all required ones
                errors["base"] = "invalid_manual"
            else:
                # Search path
                query = user_input.get("city_query", "").strip()
                if len(query) < _MIN_QUERY_LENGTH:
                    errors["city_query"] = "min_length"
                else:
                    results = await self.hass.async_add_executor_job(
                        _search_cities, query
                    )
                    if not results:
                        errors["city_query"] = "no_results"
                    elif len(results) > _MAX_RESULTS:
                        errors["city_query"] = "too_many_results"
                    else:
                        self._search_results = results
                        return await self.async_step_select_city()

        schema = self._build_user_schema(user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    def _build_user_schema(
        self, user_input: dict[str, Any] | None = None
    ) -> vol.Schema:
        """Build schema for step_user with dynamic calendar selector."""
        cal_default = (
            user_input.get(CONF_CALENDAR_ENTITY) if user_input else vol.UNDEFINED
        )

        # Discover existing calendar entities
        calendar_options = self._get_calendar_options()

        schema_dict: dict[Any, Any] = {
            vol.Optional("city_query", default=""): str,
            vol.Optional(CONF_CREATE_CALENDAR, default=True): bool,
        }

        if calendar_options:
            schema_dict[vol.Optional(CONF_CALENDAR_ENTITY, default=cal_default)] = (
                vol.In(calendar_options)
            )
        else:
            schema_dict[vol.Optional(CONF_CALENDAR_ENTITY, default=cal_default)] = str

        schema_dict[vol.Optional("manual")] = section(
            vol.Schema(
                {
                    vol.Optional(CONF_PROVINCE_GAID, default=0): int,
                    vol.Optional(CONF_DISTRICT_GAID, default=0): int,
                    vol.Optional(CONF_COMMUNE_GAID, default=0): int,
                    vol.Optional(CONF_CITY_AREA_ID, default=0): int,
                }
            ),
            {"collapsed": True},
        )

        return vol.Schema(schema_dict)

    def _get_calendar_options(self) -> dict[str, str]:
        """Return {entity_id: friendly_name} for all calendar entities."""
        pairs = [
            (s.entity_id, s.name or s.entity_id)
            for s in self.hass.states.async_all()
            if s.entity_id.startswith("calendar.")
        ]
        pairs.sort(key=lambda p: unicodedata.normalize("NFKD", p[1]).casefold())
        return dict(pairs)

    # ---------- step 2: select city from results ----------

    async def async_step_select_city(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select city from search results."""
        if user_input is not None:
            if user_input.get("city") == _BACK_OPTION:
                return await self.async_step_user()

            selected_gaid = int(user_input["city"])
            city = next(
                (r for r in self._search_results if r["gaid"] == selected_gaid),
                None,
            )
            if city is None:
                return await self.async_step_user()

            self._selected_city = city
            self._city_areas_map = await self.hass.async_add_executor_job(
                _load_city_areas
            )

            if city["district_gaid"] in self._city_areas_map:
                return await self.async_step_select_area()

            return await self._async_create_entry(city_area_id=0)

        options: dict[str, str] = {
            _BACK_OPTION: "\u2190",
        }
        options.update(
            {
                str(r["gaid"]): (
                    f"{r['name']} "
                    f"(Woj. {r['province_name']}, "
                    f"Pow. {r['district_name']}, "
                    f"Gm. {r['commune_name']})"
                )
                for r in self._search_results
            }
        )

        return self.async_show_form(
            step_id="select_city",
            data_schema=vol.Schema({vol.Required("city"): vol.In(options)}),
        )

    # ---------- step 3: optional area (dzielnica) ----------

    async def async_step_select_area(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select dzielnica for cities that have areas."""
        district_gaid = self._selected_city["district_gaid"]
        areas = self._city_areas_map.get(district_gaid, [])

        if user_input is not None:
            return await self._async_create_entry(
                city_area_id=int(user_input["city_area"])
            )

        options = {str(a["AreaId"]): a["Name"] for a in areas}

        return self.async_show_form(
            step_id="select_area",
            data_schema=vol.Schema({vol.Required("city_area"): vol.In(options)}),
        )

    # ---------- entry creation ----------

    async def _async_create_entry(self, city_area_id: int) -> FlowResult:
        """Create config entry from CSV-selected city."""
        city = self._selected_city

        unique_id = f"{city['gaid']}_{city_area_id}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        title = city["name"]
        if city_area_id:
            district_gaid = city["district_gaid"]
            areas = self._city_areas_map.get(district_gaid, [])
            area_name = next(
                (a["Name"] for a in areas if a["AreaId"] == city_area_id),
                "",
            )
            if area_name:
                title = f"{title} - {area_name}"

        return self.async_create_entry(
            title=title,
            data=self._entry_data(
                city_gaid=city["gaid"],
                province_gaid=city["province_gaid"],
                district_gaid=city["district_gaid"],
                commune_gaid=city["commune_gaid"],
                city_name=city["name"],
                commune_name=city["commune_name"],
                district_name=city["district_name"],
                province_name=city["province_name"],
                city_area_id=city_area_id,
            ),
        )

    async def _async_create_manual_entry(
        self,
        province_gaid: int,
        district_gaid: int,
        commune_gaid: int,
        city_area_id: int,
    ) -> FlowResult:
        """Create config entry from manually entered GAIDs."""
        unique_id = f"manual_{district_gaid}_{commune_gaid}_{city_area_id}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        title = f"GAID {district_gaid}/{commune_gaid}"
        if city_area_id:
            title = f"{title}/{city_area_id}"

        return self.async_create_entry(
            title=title,
            data=self._entry_data(
                city_gaid=0,
                province_gaid=province_gaid,
                district_gaid=district_gaid,
                commune_gaid=commune_gaid,
                city_name="",
                commune_name="",
                district_name="",
                province_name="",
                city_area_id=city_area_id,
            ),
        )

    def _entry_data(self, **kwargs: Any) -> dict[str, Any]:
        """Compose the config entry data dict."""
        return {
            CONF_CITY_GAID: kwargs["city_gaid"],
            CONF_PROVINCE_GAID: kwargs["province_gaid"],
            CONF_DISTRICT_GAID: kwargs["district_gaid"],
            CONF_COMMUNE_GAID: kwargs["commune_gaid"],
            CONF_CITY_NAME: kwargs["city_name"],
            CONF_COMMUNE_NAME: kwargs["commune_name"],
            CONF_DISTRICT_NAME: kwargs["district_name"],
            CONF_PROVINCE_NAME: kwargs["province_name"],
            CONF_CITY_AREA_ID: kwargs["city_area_id"],
            CONF_CREATE_CALENDAR: self._create_calendar,
            CONF_CALENDAR_ENTITY: self._calendar_entity,
        }
