#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


class RedirectException(Exception):
    """Raise inside an endpoint handler to issue an HTTP redirect.

    The framework catches this in handle_endpoint_request and emits a Response
    with the given status code and a Location header, bypassing body serialization.
    """

    def __init__(self, location: str, status_code: int = 303) -> None:
        self.location = location
        self.status_code = status_code
        super().__init__(location)
