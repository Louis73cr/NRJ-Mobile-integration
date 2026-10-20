"""Coordinateur : authentifie, récupère les lignes et la conso de chaque numéro."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NrjApiError, NrjAuthError, NrjMobileClient
from .const import CONF_PASSWORD, CONF_USERNAME, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


def _find(usages: list[dict] | None, roaming: bool) -> dict | None:
    for u in usages or []:
        if u.get("shortCode") == "dataAmount" and bool(u.get("roaming")) == roaming:
            return u
    return None


class NrjCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Un cycle = ré-auth + lignes + conso par ligne."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name="nrjmobile", update_interval=SCAN_INTERVAL)
        self.entry = entry
        # Session partagée HA pour les appels /api (au Bearer). Le flux Keycloak,
        # lui, s'isole dans sa propre session jetable (cf. api.authenticate).
        self.client = NrjMobileClient(
            async_get_clientsession(hass),
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
        )
        self.customer_id: int | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            await self.client.authenticate()
            user = await self.client.get_user_info()
            cid = int((user or {}).get("data", {}).get("customerId"))
            self.customer_id = cid
            lines_res = await self.client.get_lines_info(cid)
        except NrjAuthError as err:
            raise UpdateFailed(f"Auth NRJ Mobile: {err}") from err
        except NrjApiError as err:
            raise UpdateFailed(str(err)) from err

        data: dict[str, Any] = {"customer_id": cid, "lines": {}}
        for line in (lines_res or {}).get("nonTerminatedItemList", []):
            msisdn = line.get("msisdn")
            bid = line.get("billingAccountId")
            if not msisdn or not bid:
                continue
            try:
                plan = await self.client.get_plan_price_detail(bid)
                conso = await self.client.get_current_consumption(bid)
                oop = await self.client.get_out_of_plan_usage(bid)
            except NrjApiError as err:
                _LOGGER.warning("Conso indisponible pour %s: %s", msisdn, err)
                continue

            cur = _find((conso or {}).get("currentPlanUsage"), False)
            mx = _find((conso or {}).get("maximumPlanUsage"), False)
            roam_cur = _find((conso or {}).get("currentPlanUsage"), True)
            roam_mx = _find((conso or {}).get("maximumPlanUsage"), True)
            used = float(cur.get("amount")) if cur and cur.get("amount") is not None else None
            limit = float(mx.get("amount")) if mx and mx.get("amount") is not None else None

            data["lines"][msisdn] = {
                "msisdn": msisdn,
                "billing_account_id": bid,
                "status": line.get("statusDescr"),
                "starred": bool(line.get("starred")),
                "plan_name": (plan or {}).get("planName"),
                "monthly_price": (plan or {}).get("monthlyPrice"),
                "contract": (plan or {}).get("contractNumber"),
                "data_used": used,
                "data_limit": limit,
                "data_remaining": None if used is None or limit is None else round(limit - used, 2),
                "threshold_reached": bool(used is not None and limit and used >= limit),
                "roaming_used": float(roam_cur.get("amount")) if roam_cur and roam_cur.get("amount") else 0.0,
                "roaming_limit": float(roam_mx.get("amount")) if roam_mx and roam_mx.get("amount") else 0.0,
                "out_of_plan_euro": float((oop or {}).get("price") or 0),
            }
        return data
