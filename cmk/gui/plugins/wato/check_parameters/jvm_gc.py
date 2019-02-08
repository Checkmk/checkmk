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
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


@rulespec_registry.register
class RulespecCheckgroupParametersJvmGc(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "jvm_gc"

    @property
    def title(self):
        return _("JVM garbage collection levels")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            help=_("This ruleset also covers Tomcat, Jolokia and JMX. "),
            elements=[
                ("CollectionTime",
                 Alternative(
                     title=_("Collection time levels"),
                     elements=[
                         Tuple(
                             title=_("Time of garbage collection in ms per minute"),
                             elements=[
                                 Integer(title=_("Warning at"), unit=_("ms"), allow_empty=False),
                                 Integer(title=_("Critical at"), unit=_("ms"), allow_empty=False),
                             ],
                         )
                     ],
                 )),
                ("CollectionCount",
                 Alternative(
                     title=_("Collection count levels"),
                     elements=[
                         Tuple(
                             title=_("Count of garbage collection per minute"),
                             elements=[
                                 Integer(title=_("Warning at"), allow_empty=False),
                                 Integer(title=_("Critical at"), allow_empty=False),
                             ],
                         )
                     ],
                 )),
            ],
        )

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Name of the virtual machine and/or<br>garbage collection type"),
            help=_("The name of the application server"),
            allow_empty=False,
        )
