#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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
    Filesize,
    Percentage,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _parameter_valuespec_k8s_pods_cpu():
    return Dictionary(elements=[
        ("system",
         Tuple(
             title=_("System CPU usage"),
             elements=[Percentage(title=_("Warning at")),
                       Percentage(title=_("Critical at"))],
         )),
        ("user",
         Tuple(
             title=_("User CPU usage"),
             elements=[Percentage(title=_("Warning at")),
                       Percentage(title=_("Critical at"))],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_pods_cpu",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_pods_cpu,
        title=lambda: _("Kubernetes Namespaced pods cpu usage"),
    ))


def _parameter_valuespec_k8s_pods_memory():
    return Dictionary(elements=[
        ("rss",
         Tuple(
             title=_("Resident memory usage"),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
        ("swap",
         Tuple(
             title=_("Swap memory usage"),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
        ("usage_bytes",
         Tuple(
             title=_("Total memory usage"),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_pods_memory",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_pods_memory,
        title=lambda: _("Kubernetes Namespaced pods memory usage"),
    ))


def _parameter_valuespec_k8s_pods_fs():
    return Dictionary(elements=[
        ("usage_bytes",
         Tuple(
             title=_("Filesystem usage"),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_pods_fs",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_pods_fs,
        title=lambda: _("Kubernetes Namespaced pods Filesystem usage"),
    ))
