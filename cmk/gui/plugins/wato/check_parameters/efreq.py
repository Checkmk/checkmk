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


def _item_spec_efreq():
    return TextInput(
        title=_("Phase"), help=_("The identifier of the phase the power is related to.")
    )


def _parameter_valuespec_efreq():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_lower",
                    Tuple(
                        title=_("Lower levels"),
                        help=_(
                            "Levels for the nominal frequencies of AC devices "
                            "like UPSs or PDUs. Several phases may be addressed independently."
                        ),
                        elements=[
                            Float(
                                title=_("warning if below"),
                                unit="Hz",
                                default_value=49.0,
                                allow_int=True,
                            ),
                            Float(
                                title=_("critical if below"),
                                unit="Hz",
                                default_value=48.5,
                                allow_int=True,
                            ),
                        ],
                    ),
                ),
                (
                    "levels_upper",
                    Tuple(
                        title=_("Upper levels"),
                        help=_(
                            "Upper levels for the nominal frequencies of AC devices "
                            "like UPSs or PDUs. Leave unset where over-frequency is not a concern."
                        ),
                        elements=[
                            Float(
                                title=_("warning if above"),
                                unit="Hz",
                                default_value=51.0,
                                allow_int=True,
                            ),
                            Float(
                                title=_("critical if above"),
                                unit="Hz",
                                default_value=51.5,
                                allow_int=True,
                            ),
                        ],
                    ),
                ),
            ],
            optional_keys=("levels_lower", "levels_upper"),
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels_lower": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="efreq",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_efreq,
        parameter_valuespec=_parameter_valuespec_efreq,
        title=lambda: _("Nominal frequencies"),
    )
)
