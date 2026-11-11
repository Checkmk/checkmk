#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The cookie that remembers when the user was last asked about product usage analytics

The pop-up is shown once the timestamp in the cookie is older than the reminder interval. The
server sets the cookie on the first visit. The pop-up resets it when the user defers the decision.
"""

import datetime
from typing import Final

from cmk.ccc.site import url_prefix
from cmk.gui.http import Request, Response

COOKIE_NAME: Final = "product_usage_analytics_popup_timestamp"
COOKIE_MAX_AGE_SECONDS: Final = 2 * 365 * 24 * 60 * 60
REMINDER_INTERVAL_SECONDS: Final = 30 * 24 * 60 * 60


def set_user_product_usage_analytics_popup_cookie(request: Request, response: Response) -> None:
    response.set_cookie(
        COOKIE_NAME,
        str(datetime.datetime.now().timestamp()),
        path=url_prefix(),
        secure=request.is_secure,
        max_age=COOKIE_MAX_AGE_SECONDS,
    )


def product_usage_analytics_popup_timestamp_cookie(
    request: Request,
) -> float | None:
    cookie_value: str | None = request.cookies.get(COOKIE_NAME)
    if not cookie_value:
        return None
    return float(cookie_value)
