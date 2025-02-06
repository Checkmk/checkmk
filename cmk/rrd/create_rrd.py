#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: rrdtool is missing type hints


from cmk.base.utils import register_sigint_handler  # pylint: disable=cmk-module-layer-violation

from .config import RRDConfigImpl  # pylint: disable=cmk-module-layer-violation
from .interface import RRDInterface  # pylint: disable=cmk-module-layer-violation
from .rrd import RRDCreator  # pylint: disable=cmk-module-layer-violation


def create_rrd(rrd_interface: RRDInterface) -> None:
    register_sigint_handler()
    RRDCreator(rrd_interface).create_rrds_keepalive(config=RRDConfigImpl())
