"""Tauron WAAPI outage fetcher."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .const import FETCH_RANGE_DAYS, TAURON_OUTAGES_URL

_LOGGER = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 30
_HTTP_OK = 200


@dataclass(slots=True)
class OutageParams:
    """Query parameters for the Tauron outages endpoint."""

    province_gaid: int
    district_gaid: int
    commune_gaid: int
    city_area_id: int


@dataclass(slots=True)
class Outage:
    """Single parsed outage item from the API response."""

    outage_id: str
    start_date: datetime
    end_date: datetime
    message: str
    type_id: int
    is_active: bool


class TauronOutageFetcher:
    """Fetch and parse outages from the Tauron WAAPI."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize with an aiohttp session."""
        self._session = session

    async def fetch_outages(self, params: OutageParams) -> list[Outage]:
        """Fetch outages for the given location parameters."""
        url = self._build_url(params)
        _LOGGER.debug("Tauron WAAPI request: %s", url)
        try:
            async with self._session.get(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "HomeAssistant/TauronAwarie",
                },
                timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT),
            ) as resp:
                if resp.status != _HTTP_OK:
                    _LOGGER.error(
                        "Tauron WAAPI HTTP %s for %s", resp.status, url
                    )
                    return []
                data = await resp.json()
                return self._parse(data)
        except aiohttp.ClientError:
            _LOGGER.exception("Tauron WAAPI network error")
        except Exception:
            _LOGGER.exception("Tauron WAAPI unexpected error")
        return []

    @staticmethod
    def _build_url(params: OutageParams) -> str:
        """Construct the WAAPI URL with query parameters."""
        now = datetime.now(UTC)
        end = now + timedelta(days=FETCH_RANGE_DAYS)
        query: dict[str, int | str] = {
            "provinceGAID": params.province_gaid,
            "districtGAID": params.district_gaid,
            "fromDate": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "toDate": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }
        if params.city_area_id:
            query["cityAreaId"] = params.city_area_id
        else:
            query["communeGAID"] = params.commune_gaid
        return f"{TAURON_OUTAGES_URL}?{urlencode(query)}"

    @staticmethod
    def _parse(data: dict[str, Any]) -> list[Outage]:
        """Parse the WAAPI JSON response into Outage objects."""
        outages: list[Outage] = []
        for item in data.get("OutageItems") or []:
            try:
                outages.append(
                    Outage(
                        outage_id=item["OutageId"],
                        start_date=datetime.fromisoformat(item["StartDate"]),
                        end_date=datetime.fromisoformat(item["EndDate"]),
                        message=item.get("Message", ""),
                        type_id=item.get("TypeId", 0),
                        is_active=item.get("IsActive", True),
                    )
                )
            except (KeyError, ValueError) as err:
                _LOGGER.debug("Skip malformed outage item: %s", err)
        return outages
