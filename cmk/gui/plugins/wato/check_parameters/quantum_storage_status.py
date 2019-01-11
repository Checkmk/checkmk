#!/usr/bin/python
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

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    MonitoringState,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersStorage,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "quantum_storage_status",
    _("Quantum Storage Status"),
    Dictionary(elements=[
        ("map_states",
         Dictionary(
             elements=[
                 ("unavailable", MonitoringState(title=_("Device unavailable"), default_value=2)),
                 ("available", MonitoringState(title=_("Device available"), default_value=0)),
                 ("online", MonitoringState(title=_("Device online"), default_value=0)),
                 ("offline", MonitoringState(title=_("Device offline"), default_value=2)),
                 ("going online", MonitoringState(title=_("Device going online"), default_value=1)),
                 ("state not available",
                  MonitoringState(title=_("Device state not available"), default_value=3)),
             ],
             title=_('Map Device States'),
             optional_keys=[],
         )),
    ]),
    None,
    "dict",
)
