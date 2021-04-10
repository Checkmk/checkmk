#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
