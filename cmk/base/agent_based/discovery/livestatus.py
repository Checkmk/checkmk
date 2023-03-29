#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import socket
import time

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.type_defs import HostName

import cmk.base.config as config

__all__ = ["schedule_discovery_check"]


def schedule_discovery_check(host_name: HostName) -> None:
    now = int(time.time())
    service = (
        "Check_MK Discovery"
        if "cmk_inventory" in config.use_new_descriptions_for
        else "Check_MK inventory"
    )
    # Ignore missing check and avoid warning in cmc.log
    cmc_try = ";TRY" if config.monitoring_core == "cmc" else ""
    command = f"SCHEDULE_FORCED_SVC_CHECK;{host_name};{service};{now}{cmc_try}"

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(cmk.utils.paths.livestatus_unix_socket)
        s.send(f"COMMAND [{now}] {command}\n".encode())
    except Exception:
        if cmk.utils.debug.enabled():
            raise
