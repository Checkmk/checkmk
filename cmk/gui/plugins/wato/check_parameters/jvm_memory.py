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
    Filesize,
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


def _item_spec_jvm_memory():
    return TextAscii(
        title=_("Name of the virtual machine"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _transform_legacy_parameters_jvm_memory(params):
    # These old parameters only applied to the depricated jolokia_metrics.mem service
    # NOT to jolokia_jvm_memory(.pools).
    # However, absolute values were lower levels for *free* memory,
    # which makes no sense if no max-value for memory is known. We therefore dismiss those.
    if isinstance(params, tuple) and isinstance(params[0], float):
        return {"perc_total": params}

    new_params = {}
    for key, newkey in (
        ("totalheap", "perc_total"),
        ("heap", "perc_heap"),
        ("nonheap", "perc_nonheap"),
    ):
        levels = params.get(key)
        if isinstance(levels, tuple) and isinstance(levels[0], float):
            new_params[newkey] = levels
    return new_params


def _get_memory_level_elements(mem_type):
    return [
        ("perc_%s" % mem_type,
         Tuple(
             title=_("Percentual levels for %s memory" % mem_type),
             elements=[
                 Percentage(title=_("Warning at"),
                            label=_("% usage"),
                            default_value=80.0,
                            maxvalue=None),
                 Percentage(title=_("Critical at"),
                            label=_("% usage"),
                            default_value=90.0,
                            maxvalue=None),
             ],
         )),
        ("abs_%s" % mem_type,
         Tuple(
             title=_("Absolute levels for %s memory" % mem_type),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
    ]


def _parameter_valuespec_jvm_memory():
    return Transform(Dictionary(
        help=(_("This rule allows to set the warn and crit levels of the heap / "
                "non-heap and total memory area usage on web application servers.") + " " +
              _("Other keywords for this rule: %s") % "Tomcat, Jolokia, JMX"),
        elements=sum(
            (_get_memory_level_elements(mem_type) for mem_type in ("heap", "nonheap", "total")),
            []),
    ),
                     forth=_transform_legacy_parameters_jvm_memory)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_memory",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_memory,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_memory,
        title=lambda: _("JVM memory levels"),
    ))


def _item_spec_jvm_memory_pools():
    return TextAscii(
        title=_("Name of the memory pool"),
        help=_("The name of the memory pool in the format 'INSTANCE Memory Pool POOLNAME'"),
        allow_empty=False,
    )


def _parameter_valuespec_jvm_memory_pools():
    return Dictionary(help=(_("This rule allows to set the warn and crit levels of the memory"
                              " pools on web application servers.") + " " +
                            _("Other keywords for this rule: %s") % "Tomcat, Jolokia, JMX"),
                      elements=_get_memory_level_elements("used"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_memory_pools",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_memory_pools,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_memory_pools,
        title=lambda: _("JVM memory pool levels"),
    ))
