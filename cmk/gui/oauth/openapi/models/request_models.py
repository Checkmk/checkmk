#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from pydantic import StringConstraints

from cmk.gui.openapi.framework.model import api_field, api_model

_CookieValue = Annotated[str, StringConstraints(min_length=1, max_length=1024)]


@api_model
class IdentifySessionRequest:
    session_cookie: _CookieValue = api_field(
        description="The value of the auth_<site> cookie the browser sent.",
        example="cmkadmin:4f1c2b1e-0d7a-4a3b-9a55-8d9d7c3a2b10:9c1e...",
    )
