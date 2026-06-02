#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Self

from httpx import Response

from scripts.html_validation.lib.exceptions import AuthMissingError


@dataclasses.dataclass(frozen=True, kw_only=True)
class ResponseInfo:
    url: str
    status_code: int
    content_type: str
    redirect_location: str

    @classmethod
    def from_response(cls, resp: Response) -> Self:
        return cls(
            url=str(resp.url),
            status_code=resp.status_code,
            content_type=str(resp.headers.get("content-type", "")),
            redirect_location=resp.headers.get("location", ""),
        )

    @property
    def is_html_document(self) -> bool:
        return "text/html" in self.content_type

    @property
    def is_redirect_to_login(self) -> bool:
        return "login.py" in self.redirect_location


def build_auth_cookies(
    auth_key: str, auth_val: str, no_auth: bool = False
) -> dict[str, str] | None:
    auth_missing = not auth_key or not auth_val

    if auth_missing and not no_auth:
        raise AuthMissingError("Missing auth credentials. Either pass or set in environment.")

    return None if no_auth else {auth_key: auth_val}
