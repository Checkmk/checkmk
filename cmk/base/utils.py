#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""This is an unsorted collection of functions which are needed in
Check_MK modules and/or cmk.base modules code."""

import signal
from types import FrameType  # pylint: disable=unused-import
from typing import Text, NoReturn, Optional, Union, TYPE_CHECKING  # pylint: disable=unused-import

from cmk.utils.exceptions import MKTerminate
# TODO: Cleanup all imports of cmk.base.utils.* and purge these intermediate imports
from cmk.utils.type_defs import HostName, HostAddress, ServiceName, MetricName, CheckPluginName  # pylint: disable=unused-import

# TODO: Try to find a better place for them.


def worst_service_state(*states):
    # type: (int) -> int
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
def _handle_keepalive_interrupt(signum, frame):
    # type: (int, Optional[FrameType]) -> NoReturn
    raise MKTerminate()


def register_sigint_handler():
    # type: () -> None
    signal.signal(signal.SIGINT, _handle_keepalive_interrupt)
