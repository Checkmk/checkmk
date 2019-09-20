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
    Integer,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def transform_ibm_svc_host(params):
    if params is None:
        # Old inventory rule until version 1.2.7
        # params were None instead of emtpy dictionary
        params = {'always_ok': False}

    if 'always_ok' in params:
        if params['always_ok'] is False:
            params = {'degraded_hosts': (1, 1), 'offline_hosts': (1, 1), 'other_hosts': (1, 1)}
        else:
            params = {}
    return params


def _parameter_valuespec_ibm_svc_host():
    return Transform(
        Dictionary(elements=[
            (
                "active_hosts",
                Tuple(
                    title=_("Count of active hosts"),
                    elements=[
                        Integer(title=_("Warning at or below"), minvalue=0, unit=_("active hosts")),
                        Integer(title=_("Critical at or below"), minvalue=0,
                                unit=_("active hosts")),
                    ],
                ),
            ),
            (
                "inactive_hosts",
                Tuple(
                    title=_("Count of inactive hosts"),
                    elements=[
                        Integer(title=_("Warning at or above"),
                                minvalue=0,
                                unit=_("inactive hosts")),
                        Integer(title=_("Critical at or above"),
                                minvalue=0,
                                unit=_("inactive hosts")),
                    ],
                ),
            ),
            (
                "degraded_hosts",
                Tuple(
                    title=_("Count of degraded hosts"),
                    elements=[
                        Integer(title=_("Warning at or above"),
                                minvalue=0,
                                unit=_("degraded hosts")),
                        Integer(title=_("Critical at or above"),
                                minvalue=0,
                                unit=_("degraded hosts")),
                    ],
                ),
            ),
            (
                "offline_hosts",
                Tuple(
                    title=_("Count of offline hosts"),
                    elements=[
                        Integer(title=_("Warning at or above"), minvalue=0,
                                unit=_("offline hosts")),
                        Integer(title=_("Critical at or above"),
                                minvalue=0,
                                unit=_("offline hosts")),
                    ],
                ),
            ),
            (
                "other_hosts",
                Tuple(
                    title=_("Count of other hosts"),
                    elements=[
                        Integer(title=_("Warning at or above"), minvalue=0, unit=_("other hosts")),
                        Integer(title=_("Critical at or above"), minvalue=0, unit=_("other hosts")),
                    ],
                ),
            ),
        ],),
        forth=transform_ibm_svc_host,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ibm_svc_host",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_svc_host,
        title=lambda: _("IBM SVC Hosts"),
    ))
