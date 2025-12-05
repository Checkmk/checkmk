#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

from cmk.ccc.site import url_prefix
from cmk.gui.http import Request, Response


def set_user_product_telemetry_popup_cookie(request: Request, response: Response) -> None:
    ct = datetime.datetime.now().timestamp()
    value = str(ct)
    response.set_cookie(
        "product_telemetry_popup_timestamp", value, path=url_prefix(), secure=request.is_secure
    )


def product_telemetry_popup_timestamp_cookie(
    request: Request,
) -> float | None:
    cookie_value: str | None = request.cookies.get("product_telemetry_popup_timestamp")
    if not cookie_value:
        return None
    return float(cookie_value)
