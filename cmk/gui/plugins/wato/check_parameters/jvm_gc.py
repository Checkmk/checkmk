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
    Float,
    Percentage,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_jvm_gc():
    return TextAscii(
        title=_("Name of the virtual machine and/or<br>garbage collection type"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def transform_units(params):
    """transform 1/min to 1/s and ms/min to %"""
    if "CollectionTime" in params:
        ms_per_min = params.pop("CollectionTime")
        params["collection_time"] = (ms_per_min[0] / 600.0, ms_per_min[1] / 600.0)
    if "CollectionCount" in params:
        count_rate_per_min = params.pop("CollectionCount")
        params["collection_count"] = (count_rate_per_min[0] / 60.0, count_rate_per_min[1] / 60.0)
    return params


def _parameter_valuespec_jvm_gc():
    return Transform(
        Dictionary(
            help=_("This ruleset also covers Tomcat, Jolokia and JMX. "),
            elements=[
                ("collection_time",
                 Tuple(
                     title=_("Time spent collecting garbage in percent"),
                     elements=[
                         Percentage(title=_("Warning at")),
                         Percentage(title=_("Critical at")),
                     ],
                 )),
                ("collection_count",
                 Tuple(
                     title=_("Count of garbage collections per second"),
                     elements=[
                         Float(title=_("Warning at")),
                         Float(title=_("Critical at")),
                     ],
                 )),
            ],
        ),
        forth=transform_units,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_gc",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_gc,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_gc,
        title=lambda: _("JVM garbage collection levels"),
    ))
