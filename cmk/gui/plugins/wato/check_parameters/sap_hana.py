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
    Alternative,
    Tuple,
    Age,
    FixedValue,
    TextAscii,
    Filesize,
    Percentage,
    CascadingDropdown,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _item_spec_sap_hana_backup():
    return TextAscii(title=_("The instance name and backup type"))


def _parameter_valuespec_sap_hana_backup():
    return Dictionary(elements=[
        ('backup_age',
         Alternative(title=_("Upper levels for the backup age"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Age(title=_("Warning at")),
                                   Age(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sap_hana_backup",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_sap_hana_backup,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sap_hana_backup,
        title=lambda: _("SAP HANA Backup"),
    ))


def _item_spec_sap_hana_license():
    return TextAscii(title=_("The instance name"))


def _parameter_valuespec_sap_hana_license():
    return Dictionary(elements=[
        ('license_size',
         Alternative(title=_("Upper levels for the license size"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Filesize(title=_("Warning at")),
                                   Filesize(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
        ('license_usage_perc',
         Alternative(title=_("Upper levels for the license usage"),
                     style="dropdown",
                     elements=[
                         Tuple(title=_("Set levels"),
                               elements=[
                                   Percentage(title=_("Warning at")),
                                   Percentage(title=_("Critical at")),
                               ]),
                         Tuple(title=_("No levels"),
                               elements=[
                                   FixedValue(None, totext=""),
                                   FixedValue(None, totext=""),
                               ]),
                     ])),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sap_hana_license",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_sap_hana_license,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sap_hana_license,
        title=lambda: _("SAP HANA License"),
    ))


def _parameter_valuespec_sap_hana_memory():
    return Dictionary(
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
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sap_hana_memory",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("The instance name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sap_hana_memory,
        title=lambda: _("SAP HANA Memory"),
    ))
