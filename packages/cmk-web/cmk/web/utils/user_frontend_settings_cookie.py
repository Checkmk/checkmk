#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import urllib.parse
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from cmk.ccc.site import url_prefix
from cmk.web.context import RequestProtocol, ResponseProtocol


@dataclass(frozen=True, kw_only=True)
class UserFrontendConfig:
    # Mirrors the TypeScript UserFrontendConfig the frontend reads the cookie with, which
    # is generated from packages/cmk-shared-typing/source/user_frontend_config.json.
    hide_contextual_help_icon: bool | None
    dismissed_warnings: Sequence[str] | None = None


def set_user_frontend_config_cookie(
    request: RequestProtocol, response: ResponseProtocol, conf: UserFrontendConfig
) -> None:
    # Cookies need to be encoded, things like commas are not allowed etc.
    data = urllib.parse.quote(json.dumps({k: v for k, v in asdict(conf).items() if v is not None}))
    response.set_cookie("user_frontend_config", data, path=url_prefix(), secure=request.is_secure)
