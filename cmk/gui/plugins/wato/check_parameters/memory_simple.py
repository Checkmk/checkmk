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
    CascadingDropdown,
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
    RulespecGroupCheckParametersOperatingSystem,
)


def _item_spec_memory_simple():
    return TextAscii(
        title=_("Module name or empty"),
        help=_("Leave this empty for systems without modules, which just "
               "have one global memory usage."),
        allow_empty=True,
    )


def _parameter_valuespec_memory_simple():
    return Transform(
        Dictionary(
            help=_("Memory levels for simple devices not running more complex OSs"),
            elements=[
                ("levels",
                 CascadingDropdown(
                     title=_("Levels for memory usage"),
                     choices=[
                         ("perc_used", _("Percentual levels for used memory"),
                          Tuple(elements=[
                              Percentage(title=_("Warning at a memory usage of"),
                                         default_value=80.0,
                                         maxvalue=None),
                              Percentage(title=_("Critical at a memory usage of"),
                                         default_value=90.0,
                                         maxvalue=None)
                          ],)),
                         ("abs_free", _("Absolute levels for free memory"),
                          Tuple(elements=[
                              Filesize(title=_("Warning below")),
                              Filesize(title=_("Critical below"))
                          ],)),
                         ("ignore", _("Do not impose levels")),
                     ],
                 )),
            ],
            optional_keys=[],
        ),
        # Convert default levels from discovered checks
        forth=lambda v: not isinstance(v, dict) and {"levels": ("perc_used", v)} or v,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="memory_simple",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=_item_spec_memory_simple,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_simple,
        title=lambda: _("Main memory usage of simple devices"),
    ))
