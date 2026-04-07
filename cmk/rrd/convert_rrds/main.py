#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.rrd.config import read_hostnames, RRDConfig
from cmk.rrd.fs import RRDPaths
from cmk.rrd.interface import RRDInterface
from cmk.rrd.rrd import RRDConverter


def convert_rrds(
    rrd_interface: RRDInterface,
    hostnames: Sequence[HostName],
    split: bool,
    delete: bool,
    omd_root: Path,
) -> None:
    if not hostnames:
        hostnames = read_hostnames()

    rrd_paths = RRDPaths.from_omd_root(omd_root)
    for hostname in hostnames:
        RRDConverter(rrd_interface, hostname, rrd_paths).convert_rrds_of_host(
            RRDConfig(hostname),
            split=split,
            delete=delete,
        )
