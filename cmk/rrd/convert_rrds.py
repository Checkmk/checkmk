#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.ccc.hostaddress import HostName

from .config import read_hostnames, RRDConfig
from .interface import RRDInterface
from .rrd import RRDConverter


def convert_rrds(
    rrd_interface: RRDInterface,
    hostnames: Sequence[HostName],
    split: bool,
    delete: bool,
) -> None:
    if not hostnames:
        hostnames = read_hostnames()

    for hostname in hostnames:
        RRDConverter(rrd_interface, hostname).convert_rrds_of_host(
            RRDConfig(hostname),
            split=split,
            delete=delete,
        )
