#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Float, Migrate, TextInput, Tuple


def _item_spec_evolt():
    return TextInput(
        title=_("Phase"), help=_("The identifier of the phase the power is related to.")
    )


def _parameter_valuespec_evolt():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_lower",
                    Tuple(
                        title=_("Lower voltage levels"),
                        help=_(
                            "Voltage levels for devices like UPS or PDUs. "
                            "Several phases may be addressed independently."
                        ),
                        elements=[
                            Float(title=_("Warning at/below"), unit="V", default_value=215),
                            Float(title=_("Critical at/below"), unit="V", default_value=210),
                        ],
                    ),
                ),
                (
                    "levels_upper",
                    Tuple(
                        title=_("Upper voltage levels"),
                        help=_(
                            "Upper voltage levels for devices like UPS or PDUs. "
                            "Leave unset on installations where over-voltage is not a concern."
                        ),
                        elements=[
                            Float(title=_("Warning at/above"), unit="V", default_value=245),
                            Float(title=_("Critical at/above"), unit="V", default_value=250),
                        ],
                    ),
                ),
            ],
            optional_keys=("levels_lower", "levels_upper"),
        ),
        migrate=lambda p: (
            p if isinstance(p, dict) else {"levels_lower": (float(p[0]), float(p[1]))}
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="evolt",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_evolt,
        parameter_valuespec=_parameter_valuespec_evolt,
        title=lambda: _("Voltage levels (UPS / PDU / other devices)"),
    )
)
