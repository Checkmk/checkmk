#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any


def get_state_assumption_key(
    site: Any, host: Any, service: Any
) -> tuple[Any, Any] | tuple[Any, Any, Any]:
    if service:
        return (site, host, service)
    return (site, host)
