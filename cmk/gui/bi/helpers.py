#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def get_state_assumption_key(
    site: str, host: str, service: str | None
) -> tuple[str, str] | tuple[str, str, str]:
    if service:
        return (site, host, service)
    return (site, host)
