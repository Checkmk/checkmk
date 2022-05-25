#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, NoReturn, Optional

from cmk.utils.type_defs import HostName, KeepaliveAPI, ServiceDetails, ServiceName, ServiceState
from cmk.utils.version import Edition


def get_keepalive(edition: Edition) -> KeepaliveAPI:
    if edition is Edition.CRE:
        return NoOpKeepaliveDummy()

    import cmk.base.cee.keepalive as keepalive  # type: ignore[import] # pylint: disable=no-name-in-module

    return keepalive


class NoOpKeepaliveDummy:
    def enabled(self) -> Literal[False]:
        return False

    def add_check_result(
        self,
        host: HostName,
        service: ServiceName,
        state: ServiceState,
        output: ServiceDetails,
        cache_info: Optional[tuple[int, int]],
    ) -> NoReturn:
        raise NotImplementedError("Keepalive not available")
