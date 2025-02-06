#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.utils.hostaddress import HostName

from cmk.base import config  # pylint: disable=cmk-module-layer-violation

from .config import RRDConfigImpl  # pylint: disable=cmk-module-layer-violation
from .interface import RRDInterface  # pylint: disable=cmk-module-layer-violation
from .rrd import RRDConverter  # pylint: disable=cmk-module-layer-violation


def convert_rrds(
    rrd_interface: RRDInterface,
    hostnames: Sequence[HostName],
    split: bool,
    delete: bool,
) -> None:
    config.load(with_conf_d=True)
    rrd_config = RRDConfigImpl()

    if not hostnames:
        hostnames = rrd_config.get_hosts()

    for hostname in hostnames:
        RRDConverter(rrd_interface, hostname).convert_rrds_of_host(
            rrd_config,
            split=split,
            delete=delete,
        )
