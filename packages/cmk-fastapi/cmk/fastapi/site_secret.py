#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from collections.abc import Generator
from pathlib import Path
from typing import Final, override

import httpx2

from cmk.password_store.v1 import Secret

_SITE_INTERNAL_SECRET_REL_PATH: Final = Path("etc/site_internal.secret")


class NoSiteSecret(Exception):
    """The site secret file is missing or empty, so a request cannot be authenticated."""


class SiteSecretAuth(httpx2.Auth):
    """Sends the site-internal secret with every request, read from disk right before.

    Every request means every request to the GUI, not every request the service receives.
    A service keeps the answer for a session in an IdentityCache, and asks the GUI again only
    when it expires.
    """

    def __init__(self, omd_root: Path) -> None:
        self._omd_root = omd_root

    @override
    def auth_flow(self, request: httpx2.Request) -> Generator[httpx2.Request, httpx2.Response]:
        if (secret := _read_site_secret(self._omd_root)) is None:
            raise NoSiteSecret
        request.headers["Authorization"] = (
            f"InternalToken {base64.b64encode(secret.reveal()).decode('ascii')}"
        )
        yield request


def _read_site_secret(omd_root: Path) -> Secret[bytes] | None:
    try:
        secret = (omd_root / _SITE_INTERNAL_SECRET_REL_PATH).read_bytes()
    except OSError:
        return None
    return Secret(secret) if secret else None
