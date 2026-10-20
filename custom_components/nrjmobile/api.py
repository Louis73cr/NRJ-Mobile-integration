"""Client API NRJ Mobile (LM-WSC / Maya) — async, sans dépendance HA.

Port du client Node (nrj-client.js) :
- Auth OIDC PKCE directe (sans navigateur)
- Lignes, forfaits, consommation
- FUP_RESET (rétablissement du débit 500 Go) avec garde-fou strict gratuit

Volontairement indépendant de Home Assistant pour rester testable seul
(`python3 api.py` lance un self-check hors-ligne de computeEffectiveCost).
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import re
import secrets
import uuid
from typing import Any

try:  # aiohttp est fourni par Home Assistant ; optionnel pour le self-check hors-ligne
    import aiohttp
except ModuleNotFoundError:  # pragma: no cover
    aiohttp = None  # type: ignore[assignment]

BASE_API = "https://espace-client.nrjmobile.fr/api"
KEYCLOAK = "https://oauth2.nrjmobile.fr/realms/nrj/protocol/openid-connect"
REDIRECT_URI = "https://espace-client.nrjmobile.fr/callback?url=/connexion"
RATE_LIMIT_S = 0.35  # anti-403 WAF : espacer les appels séquentiels

_ACTION_RE = re.compile(r'action="([^"]+)"')
_CODE_RE = re.compile(r"[?&#]code=([^&#]+)")


class NrjAuthError(Exception):
    """Échec d'authentification (identifiants invalides, etc.)."""


class NrjApiError(Exception):
    """Erreur HTTP sur un endpoint /api."""


def _pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


def compute_effective_cost(quote: dict[str, Any] | None) -> dict[str, float | None]:
    """Coût réellement facturé d'un devis FUP_RESET.

    Le backend chiffre un frais brut (quotePriceDetail.total, ex 12 € TTC) puis
    applique une remise équivalente (discountAppliedTaxTotal) -> net 0 €, ce que
    l'UI affiche. net <= 0 => rétablissement gratuit.
    """
    detail = (quote or {}).get("quotePriceDetail")
    if not detail:
        return {"gross": None, "discount": 0.0, "net": None}
    gross = float(detail.get("total") or 0)
    lines: list[dict] = list(detail.get("otherDevicePriceDetail") or [])
    for sub in detail.get("subscriptionDetailList") or []:
        lines += sub.get("otherDevicePriceDetail") or []
        lines += sub.get("deviceList") or []
        lines += sub.get("planList") or []
    discount = sum(
        float((l.get("calculatedOfferPrice") or {}).get("discountAppliedTaxTotal") or 0)
        for l in lines
    )
    return {"gross": gross, "discount": discount, "net": round(gross - discount, 2)}


class NrjMobileClient:
    """Client authentifié. Un token = ~5 min, on ré-authentifie à chaque cycle."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str):
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None
        self._session_id = str(uuid.uuid4())

    async def authenticate(self) -> None:
        verifier, challenge = _pkce()
        params = {
            "client_id": "wsc-frontend",
            "redirect_uri": REDIRECT_URI,
            "state": str(uuid.uuid4()),
            "response_mode": "fragment",
            "response_type": "code",
            "scope": "openid",
            "nonce": str(uuid.uuid4()),
            "ui_locales": "fr",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "wsctemplate": "main",
        }
        # Session jetable + cookie jar neuf : isole le flux Keycloak (sinon la
        # session HA partagée garderait la session SSO et court-circuiterait le
        # formulaire de login au cycle suivant). Les appels /api ensuite se font
        # au Bearer, sans cookie, via la session partagée (self._session).
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as auth_s:
            async with auth_s.get(
                f"{KEYCLOAK}/auth", params=params, allow_redirects=False
            ) as r1:
                html = await r1.text()
            m = _ACTION_RE.search(html)
            if not m:
                raise NrjAuthError("Formulaire Keycloak introuvable.")
            login_url = m.group(1).replace("&amp;", "&")

            async with auth_s.post(
                login_url,
                data={"username": self._username, "password": self._password, "credentialId": ""},
                allow_redirects=False,
            ) as r2:
                loc = r2.headers.get("location", "")
            cm = _CODE_RE.search(loc)
            if not cm:
                raise NrjAuthError("Identifiants NRJ Mobile invalides ou flux Keycloak modifié.")

            async with auth_s.post(
                f"{KEYCLOAK}/token",
                data={
                    "code": cm.group(1),
                    "grant_type": "authorization_code",
                    "client_id": "wsc-frontend",
                    "redirect_uri": REDIRECT_URI,
                    "code_verifier": verifier,
                },
            ) as tr:
                if tr.status != 200:
                    raise NrjAuthError(f"Échange token OIDC échoué: HTTP {tr.status}")
                self._token = (await tr.json()).get("access_token")

    async def _request(self, method: str, endpoint: str, body: Any = None) -> Any:
        await asyncio.sleep(RATE_LIMIT_S)
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Collation": "fr",
            "brand-code": "20",
            "x-source": "LM-WSC",
            "x-session-id": self._session_id,
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }
        async with self._session.request(
            method, f"{BASE_API}{endpoint}", headers=headers, json=body
        ) as resp:
            text = await resp.text()
            if not resp.ok:
                raise NrjApiError(f"HTTP {resp.status} {method} {endpoint}: {text[:200]}")
            return await resp.json() if text else None

    # --- lecture ---
    async def get_user_info(self):
        return await self._request("GET", "/auth/inquireUser")

    async def get_lines_info(self, customer_id: int):
        return await self._request("POST", "/maya/customer/linesInfo", {"custId": int(customer_id)})

    async def get_plan_price_detail(self, bid: int):
        return await self._request("POST", "/maya/account/planPriceDetailInfo", {"accountId": int(bid)})

    async def get_line_info(self, bid: int):
        return await self._request("POST", "/maya/account/lines/info", {"accountId": int(bid)})

    async def get_current_consumption(self, bid: int):
        return await self._request(
            "POST", "/maya/account/inquireCurrentConsumptionDetail", {"accountId": int(bid)}
        )

    async def get_out_of_plan_usage(self, bid: int):
        return await self._request(
            "POST", "/maya/account/inquireOutOfPlanUsageDetail", {"accountId": int(bid)}
        )

    # --- FUP reset ---
    async def get_ongoing_orders(self, customer_id: int, bid: int):
        return await self._request(
            "POST",
            "/product/inquireOngoingOrders",
            {"customerId": int(customer_id), "billingAccountId": int(bid)},
        )

    async def fup_reset(
        self, customer_id: int, bid: int, confirm: bool = False, allow_paid: bool = False
    ) -> dict[str, Any]:
        """Rétablit le débit 500 Go. Par défaut dry-run.

        confirm=False -> renvoie le devis sans soumettre.
        confirm=True  -> soumet UNIQUEMENT si net <= 0 (sauf allow_paid=True).
        """
        ongoing = await self.get_ongoing_orders(customer_id, bid)
        has_pending = isinstance(ongoing, list) and any(
            o.get("bsnInterSpec", {}).get("shortCode") == "FUP_RESET"
            and o.get("orderStatus") == "ESB"
            for o in ongoing
        )

        init = await self._request(
            "POST",
            "/businessFlow/initialize",
            {
                "businessFlowSpecShortCode": "FUP_RESET",
                "workflowName": "orderSubmit",
                "sourceAccount": {"accountId": int(bid)},
                "customer": {"custId": int(customer_id)},
                "calculateQuotePrice": True,
            },
        )
        quote = (init or {}).get("data", {}).get("quote")
        updated = await self._request("POST", "/quote/updateQuote", {"quote": quote})
        quote = (updated or {}).get("data", {}).get("quote") or quote
        try:
            priced = await self._request("POST", "/quote/updateQuotePrice", {"quote": quote})
            if (priced or {}).get("data", {}).get("quote"):
                quote = priced["data"]["quote"]
        except NrjApiError:
            pass

        cost = compute_effective_cost(quote)
        result = {
            "has_pending": has_pending,
            "gross": cost["gross"],
            "discount": cost["discount"],
            "net": cost["net"],
            "submitted": False,
            "customer_order_id": (quote or {}).get("customerOrderId"),
        }
        if not confirm:
            return result
        if has_pending:
            raise NrjApiError("Un FUP_RESET est déjà en cours (cooldown 10 min).")
        net = cost["net"]
        if net is not None and net > 0 and not allow_paid:
            raise NrjApiError(
                f"Coût net {net} € (brut {cost['gross']} - remise {cost['discount']}). "
                "Soumission bloquée (strict gratuit)."
            )
        submit = await self._request("POST", "/quote/submitQuote", quote)
        result["submitted"] = (
            (submit or {}).get("operationResult", {}).get("resultCode") == "SUCCESS"
        )
        return result


if __name__ == "__main__":
    # Self-check hors-ligne de la logique de coût (le chemin "argent").
    q = {
        "quotePriceDetail": {
            "total": 12,
            "subscriptionDetailList": [
                {"otherDevicePriceDetail": [{"calculatedOfferPrice": {"discountAppliedTaxTotal": 12}}]}
            ],
        }
    }
    assert compute_effective_cost(q) == {"gross": 12.0, "discount": 12.0, "net": 0.0}
    assert compute_effective_cost({"quotePriceDetail": {"total": 12}})["net"] == 12.0
    assert compute_effective_cost(None)["net"] is None
    print("api self-check OK")
