#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is an unsorted collection of functions which are needed in
Check_MK modules and/or cmk.base modules code."""

import signal
from types import FrameType
from typing import NoReturn, Optional

from cmk.utils.exceptions import MKTerminate

# TODO: Try to find a better place for them.


def worst_service_state(*states: int) -> int:
    """Aggregates several monitoring states to the worst state"""
    if 2 in states:
        return 2
    return max(states)


#.
#   .--Ctrl-C--------------------------------------------------------------.
#   |                     ____ _        _        ____                      |
#   |                    / ___| |_ _ __| |      / ___|                     |
#   |                   | |   | __| '__| |_____| |                         |
#   |                   | |___| |_| |  | |_____| |___                      |
#   |                    \____|\__|_|  |_|      \____|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Handling of Ctrl-C                                                  |
#   '----------------------------------------------------------------------'


# register SIGINT handler for consistent CTRL+C handling
def _handle_keepalive_interrupt(signum: int, frame: Optional[FrameType]) -> NoReturn:
    raise MKTerminate()


def register_sigint_handler() -> None:
    signal.signal(signal.SIGINT, _handle_keepalive_interrupt)
