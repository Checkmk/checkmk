#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupEnforcedServicesEnvironment,
)
from cmk.gui.valuespec import TextInput


def _item_spec_temperature_auto():
    return TextInput(
        title=_("Sensor ID"),
        help=_("The identificator of the thermal sensor."),
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="temperature_auto",
        group=RulespecGroupEnforcedServicesEnvironment,
        is_deprecated=True,
        item_spec=_item_spec_temperature_auto,
        title=lambda: _("Temperature sensors with builtin levels"),
    )
)
