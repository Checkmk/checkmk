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


def _parameter_valuespec_ibm_svc_mdiskgrp():
    return vs_filesystem(
        extra_elements=[
            (
                "provisioning_levels",
                Tuple(
                    title=_("Provisioning Levels"),
                    help=_("A provisioning of over 100% means over provisioning."),
                    elements=[
                        Percentage(
                            title=_("Warning at a provisioning of"),
                            default_value=110.0,
                            maxvalue=None,
                        ),
                        Percentage(
                            title=_("Critical at a provisioning of"),
                            default_value=120.0,
                            maxvalue=None,
                        ),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_svc_mdiskgrp",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Name of the pool"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_svc_mdiskgrp,
        title=lambda: _("IBM SVC Pool Capacity"),
    )
)
