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
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


def _parameter_valuespec_ups_capacity():
    return Dictionary(
        title=_("Levels for battery parameters"),
        optional_keys=False,
        elements=[
            (
                "capacity",
                Tuple(
                    title=_("Battery capacity"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            help=
                            _("The battery capacity in percent at and below which a warning state is triggered"
                             ),
                            unit="%",
                            default_value=95,
                        ),
                        Integer(
                            title=_("Critical at"),
                            help=
                            _("The battery capacity in percent at and below which a critical state is triggered"
                             ),
                            unit="%",
                            default_value=90,
                        ),
                    ],
                ),
            ),
            (
                "battime",
                Tuple(
                    title=_("Time left on battery"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            help=
                            _("Time left on Battery at and below which a warning state is triggered"
                             ),
                            unit=_("min"),
                            default_value=0,
                        ),
                        Integer(
                            title=_("Critical at"),
                            help=
                            _("Time Left on Battery at and below which a critical state is triggered"
                             ),
                            unit=_("min"),
                            default_value=0,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ups_capacity",
        group=RulespecGroupCheckParametersEnvironment,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ups_capacity,
        title=lambda: _("UPS Capacity"),
    ))
