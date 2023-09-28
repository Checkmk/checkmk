#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Integer, Migrate, TextInput, Tuple


def _item_spec_epower():
    return TextInput(
        title=_("Phase"), help=_("The identifier of the phase the power is related to.")
    )


def _migrate(value: tuple | dict) -> dict:
    if isinstance(value, tuple):
        return {"levels_lower": value}
    return value


def _parameter_valuespec_epower():
    return Migrate(
        Dictionary(
            [
                (
                    "levels_lower",
                    Tuple(
                        help=_(
                            "Levels for the electrical power consumption of a device "
                            "like a UPS or a PDU. Several phases may be addressed independently."
                        ),
                        elements=[
                            Integer(title=_("warning if below"), unit="Watt", default_value=20),
                            Integer(title=_("critical if below"), unit="Watt", default_value=1),
                        ],
                    ),
                ),
            ],
            optional_keys=False,
        ),
        migrate=_migrate,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="epower",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_epower,
        parameter_valuespec=_parameter_valuespec_epower,
        title=lambda: _("Electrical Power"),
    )
)
