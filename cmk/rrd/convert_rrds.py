#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.utils.hostaddress import HostName

from .config import read_hostnames, RRDConfigImpl  # pylint: disable=cmk-module-layer-violation
from .interface import RRDInterface  # pylint: disable=cmk-module-layer-violation
from .rrd import RRDConverter  # pylint: disable=cmk-module-layer-violation


def convert_rrds(
    rrd_interface: RRDInterface,
    hostnames: Sequence[HostName],
    split: bool,
    delete: bool,
) -> None:
    rrd_config = RRDConfigImpl()

    if not hostnames:
        hostnames = read_hostnames()

    for hostname in hostnames:
        RRDConverter(rrd_interface, hostname).convert_rrds_of_host(
            rrd_config,
            split=split,
            delete=delete,
        )
