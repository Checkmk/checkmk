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
    ListOf,
    Tuple,
    TextAscii,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersDiscovery,
    rulespec_registry,
    HostRulespec,
)


@rulespec_registry.register
class RulespecDiscoveryRulesVnxQuotas(HostRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersDiscovery

    @property
    def name(self):
        return "discovery_rules_vnx_quotas"

    @property
    def match_type(self):
        return "dict"

    @property
    def valuespec(self):
        return Dictionary(
            title=_("VNX quotas and filesystems discovery"),
            elements=[
                ("dms_names",
                 ListOf(
                     Tuple(elements=[
                         TextAscii(title=_("Exact RWVDMS name or regex")),
                         TextAscii(title=_("Substitution")),
                     ]),
                     title=_("Map RWVDMS names"),
                     help=_("Here you are able to substitute the RWVDMS name. Either you "
                            "determine an exact name and the related subsitution or you "
                            "enter a regex beginning with '~'. The regexes must include "
                            "groups marked by '(...)' which will be substituted."),
                 )),
                ("mp_names",
                 ListOf(
                     Tuple(elements=[
                         TextAscii(title=_("Exact mount point name or regex")),
                         TextAscii(title=_("Substitution")),
                     ]),
                     title=_("Map mount point names"),
                     help=_("Here you are able to substitute the filesystem name. Either you "
                            "determine an exact name and the related subsitution or you "
                            "enter a regex beginning with '~'. The regexes must include "
                            "groups marked by '(...)' which will be substituted."),
                 )),
            ],
            optional_keys=[],
        )
