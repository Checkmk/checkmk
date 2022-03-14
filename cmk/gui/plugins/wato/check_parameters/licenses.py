#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Alternative, FixedValue, Integer, Percentage, TextInput, Tuple


def _vs_license():
    return Alternative(
        title=_("Levels for Number of Licenses"),
        default_value=None,
        elements=[
            Tuple(
                title=_("Absolute levels for unused licenses"),
                elements=[
                    Integer(title=_("Warning below"), default_value=5, unit=_("unused licenses")),
                    Integer(title=_("Critical below"), default_value=0, unit=_("unused licenses")),
                ],
            ),
            Tuple(
                title=_("Percentual levels for unused licenses"),
                elements=[
                    Percentage(title=_("Warning below"), default_value=10.0),
                    Percentage(title=_("Critical below"), default_value=0),
                ],
            ),
            FixedValue(
                value=None,
                totext=_("Critical when all licenses are used"),
                title=_("Go critical if all licenses are used"),
            ),
            FixedValue(
                value=False,
                title=_("Always report OK"),
                totext=_("Alerting depending on the number of used licenses is disabled"),
            ),
        ],
    )


def _item_spec_citrix_licenses():
    return TextInput(
        title=_("ID of the license, e.g. <tt>PVSD_STD_CCS</tt>"),
        allow_empty=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="citrix_licenses",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_citrix_licenses,
        parameter_valuespec=_vs_license,
        title=lambda: _("Number of used Citrix licenses"),
    )
)


def _item_spec_esx_licenses():
    return TextInput(
        title=_("Name of the license"),
        help=_("For example <tt>VMware vSphere 5 Standard</tt>"),
        allow_empty=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="esx_licenses",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_esx_licenses,
        parameter_valuespec=_vs_license,
        title=lambda: _("VMware licenses"),
    )
)


def _item_spec_ibmsvc_licenses():
    return TextInput(
        title=_("ID of the license, e.g. <tt>virtualization</tt>"),
        allow_empty=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibmsvc_licenses",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_ibmsvc_licenses,
        parameter_valuespec=_vs_license,
        title=lambda: _("IBM SVC licenses"),
    )
)


def _item_spec_rds_licenses():
    return TextInput(
        title=_("ID of the license, e.g. <tt>Windows Server 2008 R2</tt>"),
        allow_empty=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="rds_licenses",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_rds_licenses,
        parameter_valuespec=_vs_license,
        title=lambda: _("Number of used Remote Desktop Licenses"),
    )
)
