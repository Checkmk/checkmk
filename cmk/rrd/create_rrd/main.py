#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import signal
from pathlib import Path
from types import FrameType
from typing import NoReturn

from cmk.ccc.exceptions import MKTerminate
from cmk.rrd.config import RRDConfig
from cmk.rrd.interface import RRDInterface
from cmk.rrd.rrd import RRDCreator


# register SIGINT handler for consistent CTRL+C handling
def _handle_keepalive_interrupt(signum: int, frame: FrameType | None) -> NoReturn:
    raise MKTerminate()


def create_rrd(rrd_interface: RRDInterface, omd_root: Path) -> None:
    signal.signal(signal.SIGINT, _handle_keepalive_interrupt)
    RRDCreator(rrd_interface, omd_root).create_rrds_keepalive(RRDConfig)
