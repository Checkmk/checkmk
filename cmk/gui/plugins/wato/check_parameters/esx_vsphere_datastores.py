#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import vs_filesystem
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Percentage, TextInput, Tuple


def _item_spec_esx_vsphere_datastores():
    return TextInput(
        title=_("Datastore Name"), help=_("The name of the Datastore"), allow_empty=False
    )


def _parameter_valuespec_esx_vsphere_datastores():
    return vs_filesystem(
        extra_elements=[
            (
                "provisioning_levels",
                Tuple(
                    title=_("Provisioning Levels"),
                    help=_(
                        "A provisioning of more than 100% is called "
                        "over provisioning and can be a useful strategy for saving disk space. But you cannot guarantee "
                        "any longer that every VM can really use all space that it was assigned. Here you can "
                        "set levels for the maximum provisioning. A warning level of 150% will warn at 50% over provisioning."
                    ),
                    elements=[
                        Percentage(
                            title=_("Warning at a provisioning of"),
                            maxvalue=None,
                            default_value=120.0,
                        ),
                        Percentage(
                            title=_("Critical at a provisioning of"),
                            maxvalue=None,
                            default_value=150.0,
                        ),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="esx_vsphere_datastores",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_esx_vsphere_datastores,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_esx_vsphere_datastores,
        title=lambda: _("ESX Datastores (used space and growth)"),
    )
)
