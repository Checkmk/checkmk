#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, override

import httpx2
from fastapi.requests import HTTPConnection
from fastapi.security import APIKeyCookie
from pydantic import BaseModel, ConfigDict, ValidationError

from cmk.ccc.site import get_apache_port, omd_site
from cmk.fastapi.site_secret import NoSiteSecret, SiteSecretAuth

logger = logging.getLogger(__name__)

# How long a logged-out or locked user can still send requests.
IDENTITY_TTL: Final = 60.0

# The longest cookie the GUI accepts.
MAX_SESSION_COOKIE_LENGTH: Final = 1024

# A user waits for this on every identity cache miss. The GUI answers in milliseconds, but
# the request is nested in the user's request on the same site Apache and can wait for a
# free Apache process first, which may still have to import the GUI.
TIMEOUT: Final = httpx2.Timeout(30.0, connect=2.0)

_IDENTIFY_PATH: Final = "domain-types/gui_session/actions/identify/invoke"


@dataclass(frozen=True, slots=True)
class Identity:
    user_id: str
    # Whether the user holds each permission the caller asked for.
    permissions: Mapping[str, bool]
    # Empty unless the caller asked for them.
    contact_groups: Sequence[str]


@dataclass(frozen=True, slots=True)
class Rejected:
    """The GUI refused the session: not logged in, expired, locked or not allowed in."""


@dataclass(frozen=True, slots=True)
class Unavailable:
    """No verdict. The reason names the endpoint, status and error code, never a body."""

    reason: str


class IdentityCache[T]:
    """What the GUI said about a session, for a limited time.

    Entries are kept by a hash of the key, which is usually the session cookie.

    The times are from a monotonic clock, so a jump of the wall clock cannot keep an
    entry alive.
    """

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._entries: dict[bytes, tuple[T, float]] = {}

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, key: str, *, now: float) -> T | None:
        digest = _digest(key)
        if (entry := self._entries.get(digest)) is None:
            return None
        value, expires_at = entry
        if now < expires_at:
            return value
        del self._entries[digest]
        return None

    def put(self, key: str, value: T, *, now: float) -> None:
        digest = _digest(key)
        # Re-inserted at the end, so expired entries collect at the front.
        self._entries.pop(digest, None)
        self._entries[digest] = (value, now + self._ttl)
        while (oldest := next(iter(self._entries))) != digest and self._entries[oldest][1] <= now:
            del self._entries[oldest]


def _digest(key: str) -> bytes:
    return hashlib.sha256(key.encode()).digest()


class SessionCookie(APIKeyCookie):
    """The GUI session cookie auth_<site>, with the site filled in when a request comes in.

    The build writes the API description without a site, so the name is unknown then.
    """

    def __init__(self) -> None:
        super().__init__(name="auth_<site>", description="The GUI session cookie")

    @override
    async def __call__(self, request: HTTPConnection) -> str | None:
        cookie = request.cookies.get(f"auth_{omd_site()}")
        # The GUI answers a longer cookie with a plain 400, which would become a 503.
        if cookie is not None and len(cookie) > MAX_SESSION_COOKIE_LENGTH:
            cookie = None
        return self.check_api_key(cookie)


def loopback_http_client(
    omd_root: Path, transport: httpx2.AsyncBaseTransport | None = None
) -> httpx2.AsyncClient:
    """An HTTP client for the internal REST API of this site's GUI, sending the site secret.

    It ignores proxy settings from the environment, which would otherwise send the
    site secret away from the loopback.
    """
    return httpx2.AsyncClient(
        base_url=f"http://localhost:{get_apache_port(omd_root)}/{omd_site()}/check_mk/api/internal/",
        auth=SiteSecretAuth(omd_root),
        trust_env=False,
        timeout=TIMEOUT,
        transport=transport,
    )


class _IdentifyAnswer(BaseModel):
    model_config = ConfigDict(strict=True)

    user_id: str
    permissions: dict[str, bool] = {}
    contact_groups: list[str] | None = None


class GuiLoopback:
    """Asks this site's GUI on behalf of a site service, over the loopback client."""

    def __init__(self, http: httpx2.AsyncClient) -> None:
        self._http = http

    async def identify(
        self,
        session_cookie: str,
        *,
        required_permissions: Sequence[str] = (),
        include_contact_groups: bool = False,
    ) -> Identity | Rejected | Unavailable:
        body: dict[str, object] = {"session_cookie": session_cookie}
        if required_permissions:
            body["required_permissions"] = list(required_permissions)
        if include_contact_groups:
            body["include_contact_groups"] = True
        identified = await self.post("identify", _IDENTIFY_PATH, body, _IdentifyAnswer)
        if isinstance(identified, Rejected | Unavailable):
            return identified
        if not set(required_permissions) <= identified.permissions.keys():
            return unavailable("identify", "status 200, the answer does not report the permission")
        if include_contact_groups and identified.contact_groups is None:
            return unavailable(
                "identify", "status 200, the answer does not report the contact groups"
            )
        return Identity(
            user_id=identified.user_id,
            permissions=identified.permissions,
            contact_groups=identified.contact_groups or [],
        )

    async def post[M: BaseModel](
        self, endpoint: str, path: str, body: Mapping[str, object], answer: type[M]
    ) -> M | Rejected | Unavailable:
        """The 200 answer to a single request, never retried, or what else came of it."""
        try:
            response = await self._http.post(path, json=body)
        except NoSiteSecret:
            return unavailable(endpoint, "there is no site secret to send")
        except httpx2.RequestError as e:
            # Only the type: the message of a request error can repeat the request.
            return unavailable(endpoint, f"no answer ({type(e).__name__})")
        if response.status_code == httpx2.codes.OK:
            try:
                return answer.model_validate_json(response.content)
            except ValidationError:
                return unavailable(
                    endpoint, "status 200, the answer does not have the expected shape"
                )
        error = _oauth_error(response)
        if response.status_code == httpx2.codes.BAD_REQUEST and error == "invalid_grant":
            return Rejected()
        return unavailable(
            endpoint, f"status {response.status_code}" + (f", error {error}" if error else "")
        )


def _oauth_error(response: httpx2.Response) -> str | None:
    """The OAuth error code the GUI puts into the ext of a problem answer, if any."""
    try:
        problem = json.loads(response.content)
    except ValueError:
        return None
    ext = problem.get("ext") if isinstance(problem, dict) else None
    error = ext.get("error") if isinstance(ext, dict) else None
    return error if isinstance(error, str) else None


def unavailable(endpoint: str, reason: str) -> Unavailable:
    logger.warning(
        "The GUI gave no verdict on %(endpoint)s: %(reason)s",
        {"endpoint": endpoint, "reason": reason},
    )
    return Unavailable(reason=f"{endpoint}: {reason}")
