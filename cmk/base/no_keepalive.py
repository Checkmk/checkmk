#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Literal, NoReturn

from cmk.utils.type_defs import HostName, ServiceDetails, ServiceName, ServiceState


class _NoKeepalive:
    def enabled(self) -> Literal[False]:
        return False

    def add_check_result(
        self,
        host: HostName,
        service: ServiceName,
        state: ServiceState,
        output: ServiceDetails,
        cache_info: tuple[int, int] | None,
    ) -> NoReturn:
        raise NotImplementedError("Keepalive not available")


NO_KEEPALIVE = _NoKeepalive()  # Singleton
