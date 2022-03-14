#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupEnforcedServicesApplications,
)
from cmk.gui.valuespec import TextInput


def _item_spec_omd_status():
    return TextInput(
        title=_("Name of the OMD site"),
        help=_("The name of the OMD site to check the status for"),
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="omd_status",
        group=RulespecGroupEnforcedServicesApplications,
        item_spec=_item_spec_omd_status,
        title=lambda: _("OMD site status"),
    )
)
