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
    Alternative,
    Checkbox,
    Dictionary,
    Integer,
    Percentage,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    HostRulespec,
)


def _valuespec_discovery_win_dhcp_pools():
    return Dictionary(
        title=_("Discovery of Windows DHCP Pools"),
        elements=[
            ("empty_pools",
             Checkbox(
                 title=_("Discovery of empty DHCP pools"),
                 label=_("Include empty pools into the monitoring"),
                 help=_("You can activate the creation of services for "
                        "DHCP pools, which contain no IP addresses."),
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_win_dhcp_pools",
        valuespec=_valuespec_discovery_win_dhcp_pools,
    ))


def _item_spec_win_dhcp_pools():
    return TextAscii(
        title=_("Pool name"),
        allow_empty=False,
    )


def _parameter_valuespec_win_dhcp_pools():
    return Transform(
        Dictionary(elements=[
            ("free_leases",
             Alternative(title=_("Free leases levels"),
                         elements=[
                             Tuple(title=_("Free leases levels in percent"),
                                   elements=[
                                       Percentage(title=_("Warning if below"), default_value=10.0),
                                       Percentage(title=_("Critical if below"), default_value=5.0)
                                   ]),
                             Tuple(title=_("Absolute free leases levels"),
                                   elements=[
                                       Integer(title=_("Warning if below"), unit=_("free leases")),
                                       Integer(title=_("Critical if below"), unit=_("free leases"))
                                   ])
                         ])),
            ("used_leases",
             Alternative(title=_("Used leases levels"),
                         elements=[
                             Tuple(title=_("Used leases levels in percent"),
                                   elements=[
                                       Percentage(title=_("Warning if below")),
                                       Percentage(title=_("Critical if below"))
                                   ]),
                             Tuple(title=_("Absolute used leases levels"),
                                   elements=[
                                       Integer(title=_("Warning if below"), unit=_("used leases")),
                                       Integer(title=_("Critical if below"), unit=_("used leases"))
                                   ])
                         ])),
        ]),
        forth=lambda params: isinstance(params, tuple) and
        {"free_leases": (float(params[0],), float(params[1],))} or params,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="win_dhcp_pools",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_win_dhcp_pools,
        parameter_valuespec=_parameter_valuespec_win_dhcp_pools,
        title=lambda: _("DHCP Pools for Windows and Linux"),
    ))
