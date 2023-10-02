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
from cmk.gui.valuespec import Dictionary, DropdownChoice, Migrate, TextInput


def _item_spec_siemens_plc_flag():
    return TextInput(
        title=_("Device Name and Value Ident"),
        help=_(
            "You need to concatenate the device name which is configured in the special agent "
            "for the PLC device separated by a space with the ident of the value which is also "
            "configured in the special agent."
        ),
        allow_empty=True,
    )


def _parameter_valuespec_siemens_plc_flag():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "expected_state",
                    DropdownChoice(
                        help=_(
                            "This rule sets the expected state, the one which should result in an OK state, "
                            "of the monitored flags of Siemens PLC devices."
                        ),
                        title=_("Expected flag state"),
                        choices=[
                            (True, _("Expect the flag to be: On")),
                            (False, _("Expect the flag to be: Off")),
                        ],
                        default_value=True,
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"expected_state": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="siemens_plc_flag",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_siemens_plc_flag,
        parameter_valuespec=_parameter_valuespec_siemens_plc_flag,
        title=lambda: _("Siemens PLC Flag state"),
    )
)
