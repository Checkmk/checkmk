#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.valuespec import Dictionary, TextInput


def _parameters_valuespec_prism_hosts():
    return Dictionary(
        elements=[
            (
                "system_state",
                TextInput(
                    title=_("Wanted Host State"),
                    allow_empty=False,
                    default_value="NORMAL",
                ),
            ),
        ],
        title=_("Wanted Host State for defined Nutanix Host"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="prism_hosts",
        item_spec=lambda: TextInput(title=_("Host")),
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameters_valuespec_prism_hosts,
        title=lambda: _("Nutanix Host State"),
    )
)
