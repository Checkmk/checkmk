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
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _parameters_valuespec_prism_vms():
    status_choice = [
        ("on", _("On")),
        ("unknown", _("Unknown")),
        ("off", _("Off")),
        ("powering_on", _("Powering on")),
        ("shutting_down", _("Shutting down")),
        ("powering_off", _("Powered Off")),
        ("pausing", _("Pausing")),
        ("paused", _("Paused")),
        ("suspending", _("Suspending")),
        ("suspended", _("Suspended")),
        ("resuming", _("Resuming")),
        ("resetting", _("Resetting")),
        ("migrating", _("Migrating")),
    ]
    return Dictionary(
        elements=[
            (
                "system_state",
                DropdownChoice(
                    title=_("Wanted VM State"),
                    choices=status_choice,
                    default_value="on",
                ),
            ),
        ],
        title=_("Wanted VM State for defined Nutanix VMs"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="prism_vm_status",
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameters_valuespec_prism_vms,
        title=lambda: _("Nutanix single VM State"),
    )
)
